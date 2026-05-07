from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from .serializers import RegisterSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):

    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()

        return Response({
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):

    return Response({
        'username': request.user.username,
        'email': request.user.email
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):

    email = request.data.get('email')

    try:
        user = User.objects.get(email=email)

        token = default_token_generator.make_token(user)

        return Response({
            'message': 'Password reset token generated',
            'token': token
        })

    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):

    email = request.data.get('email')
    token = request.data.get('token')
    new_password = request.data.get('new_password')

    try:
        user = User.objects.get(email=email)

        if default_token_generator.check_token(user, token):

            user.set_password(new_password)
            user.save()

            return Response({
                'message': 'Password reset successful'
            })

        return Response({
            'error': 'Invalid token'
        }, status=400)

    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=404)