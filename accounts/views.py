from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.models import Group
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
import cloudinary.api
from .decorators import *
from .models import *
from .serializers import *


# === Authentication ===

# Register
@api_view(['POST',])
def sign_up(request):
    if request.method == 'POST':
        serializer = RegistrationSerializer(data=request.data)

        if serializer.is_valid():

            user = serializer.save()

            group = Group.objects.get(name='normal_user')
            user.groups.add(group)

            login(request, user)


            return Response({"user": serializer.data, "token": Token.objects.get(user=user).key, "user_id": user.pk}, status=status.HTTP_201_CREATED)
        else:
            return Response({"errors": serializer._errors}, status=status.HTTP_400_BAD_REQUEST)

# Logout
@csrf_exempt 
@api_view(['POST',])
def sign_out(request):

    request.user.auth_token.delete()
    logout(request)

    return Response({"success": "Successfully logged out."}, status=status.HTTP_200_OK)

# custom method to return user_id and token when logged in
class CustomAuthToken(ObtainAuthToken):

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username
        })

# custom method to use email to login 
class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None
        else:
            if user.check_password(password):
                return user
        return None


# === Users ===

# Get User
@api_view(['GET',])
def get_user(request, id):
    try:
        user = User.objects.get(pk=id)

    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    try:
        group = Group.objects.get(user=id)

    except Group.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    

    user_serializer = UserSerializer(user)
    profile_serializer = ProfileSerializer(user.profile)
    group_serializer = GroupSerializer(group)
    

    return Response({"user": user_serializer.data, "profile": profile_serializer.data, "group": group_serializer.data}, status=status.HTTP_200_OK)

# Update User
@csrf_exempt
@api_view(['PUT',])
@permission_classes([IsAuthenticated])
def update_user(request, id):
    try:
        user = User.objects.get(pk=id)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'PUT':
        user_serializer = UserSerializer(instance=user, data=request.data)

        if user_serializer.is_valid():
            user_serializer.save()
            return Response(user_serializer.data, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Upload Photo
@csrf_exempt
@api_view(['PUT',])
@permission_classes([IsAuthenticated])
def upload_image(request, id):
    try:
        user = User.objects.get(pk=id)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        profile_serializer = ProfileSerializer(instance=user.profile, data=request.data)
        # delete previous profile photo from cloudinary before saving new one
        cloudinary.api.delete_resources(user.profile.profile_pic)

        if profile_serializer.is_valid():
            profile_serializer.save()
            return Response(profile_serializer.data, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Delete User
@csrf_exempt
@api_view(['DELETE',])
@permission_classes([IsAuthenticated])
def delete_user(request, id):
    try:
        user = User.objects.get(pk=id)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        # delete profile photo when deleting user
        cloudinary.api.delete_resources(user.profile.profile_pic)
        user.delete()
        return Response({"Deleted user successfully"}, status=status.HTTP_204_NO_CONTENT)
    else:
        return Response(user.errors, status=status.HTTP_400_BAD_REQUEST)

# Favourite Restaurant
@csrf_exempt
@api_view(['POST',])
@permission_classes([IsAuthenticated])
def favourite_restaurant(request, user_id, restaurant_id):
    if request.method == 'POST':
        try:
            user = UserProfile.objects.get(pk=user_id)
        except UserProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            restaurant = Restaurant.objects.get(pk=restaurant_id)
        except Restaurant.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    restaurant.users.add(user)
    user.favourites.add(restaurant)

    restaurant.save()
    user.save()
    

    return Response({"Successfully favourited restaurant"}, status=status.HTTP_200_OK)

# Unfavourite Restaurant
@csrf_exempt
@api_view(['POST',])
@permission_classes([IsAuthenticated])
def unfavourite_restaurant(request, user_id, restaurant_id):
    if request.method == 'POST':
        try:
            user = UserProfile.objects.get(pk=user_id)
        except UserProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            restaurant = Restaurant.objects.get(pk=restaurant_id)
        except Restaurant.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    restaurant.users.remove(user)
    user.favourites.remove(restaurant)

    restaurant.save()
    user.save()
    

    return Response({"Successfully unfavourited restaurant"}, status=status.HTTP_200_OK)


# Request to become restaurant owner
@csrf_exempt
@api_view(['POST',])
@permission_classes([IsAuthenticated])
def request_ownership(request, user_id, restaurant_id):
    if request.method == 'POST':
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            restaurant = Restaurant.objects.get(pk=restaurant_id)
        except Restaurant.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
    
    serializer = RequestSerializer(data=request.data)

    if serializer.is_valid():
        review = serializer.save()

        user.request.add(review)
        restaurant.request.add(review)

        serializer.save()
        

    return Response({"Successfully sent to admin"}, status=status.HTTP_200_OK)

# Get all request
@csrf_exempt
@api_view(['GET',])
@permission_classes([IsAuthenticated])
@admin_only
def get_request(request):

    if request.method == 'GET':
        r = Request.objects.all()

        request_serializer = RequestSerializer(r, many=True)

    return Response({"requests": request_serializer.data}, status=status.HTTP_200_OK)

# Accept request
@csrf_exempt
@api_view(['PUT',])
@permission_classes([IsAuthenticated])
@admin_only
def accept_request(request, user_id, restaurant_id):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    try:
        restaurant = Restaurant.objects.get(pk=restaurant_id)
    except Restaurant.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    user.profile.restaurant_owned.add(restaurant)
    restaurant.owners.add(user.profile)
    restaurant.is_registered = True

    group = Group.objects.get(name='normal_user')
    user.groups.remove(group)

    group1 = Group.objects.get(name='restaurant_owner')
    user.groups.add(group1)

    user.save()
    restaurant.save()

    return Response({"Successfully added restaurant owner"}, status=status.HTTP_200_OK)

# Delete Request
@csrf_exempt
@api_view(['DELETE',])
@permission_classes([IsAuthenticated])
@admin_only
def delete_request(request, id):
    try:
        r = Request.objects.get(pk=id)
    except Request.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        r.delete()
        return Response({"Deleted request successfully"}, status=status.HTTP_204_NO_CONTENT)
    else:
        return Response(user.errors, status=status.HTTP_400_BAD_REQUEST)

