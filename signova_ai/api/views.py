from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator

# ✅ Swagger imports
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


# ✅ REGISTER USER
@swagger_auto_schema(
    method='post',
    operation_description="Register a new user",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['username', 'email', 'password'],
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING),
            'email': openapi.Schema(type=openapi.TYPE_STRING, format='email'),
            'password': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):

    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    # ✅ Validate
    if not username or not email or not password:
        return Response({
            "error": "All fields are required"
        }, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({
            "error": "Username already exists"
        }, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )

    return Response({
        "message": "User registered successfully",
        "username": user.username
    }, status=status.HTTP_201_CREATED)


# ✅ USER PROFILE (Protected)
@swagger_auto_schema(
    method='get',
    operation_description="Get logged-in user profile",
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):

    return Response({
        'username': request.user.username,
        'email': request.user.email
    })


# ✅ FORGOT PASSWORD
@swagger_auto_schema(
    method='post',
    operation_description="Generate password reset token",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
)
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):

    email = request.data.get('email')

    if not email:
        return Response({
            "error": "Email is required"
        }, status=400)

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


# ✅ RESET PASSWORD
@swagger_auto_schema(
    method='post',
    operation_description="Reset user password using token",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'token', 'new_password'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'token': openapi.Schema(type=openapi.TYPE_STRING),
            'new_password': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
)
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):

    email = request.data.get('email')
    token = request.data.get('token')
    new_password = request.data.get('new_password')

    if not email or not token or not new_password:
        return Response({
            "error": "All fields are required"
        }, status=400)

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