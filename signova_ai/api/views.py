from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import User

import bcrypt


# ================================
# ✅ REGISTER USER
# ================================
@swagger_auto_schema(
    method='post',
    operation_description="Register a new user",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['username', 'email', 'password'],
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING),
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING),
            'country': openapi.Schema(type=openapi.TYPE_STRING),
            'gender': openapi.Schema(type=openapi.TYPE_STRING),
            'age': openapi.Schema(type=openapi.TYPE_INTEGER),
        },
    ),
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    country = request.data.get('country')
    gender = request.data.get('gender')
    age = request.data.get('age')

    if not username or not email or not password:
        return Response(
            {"error": "Username, email and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ✅ Check existing user
    if User.objects.filter(username=username).first():
        return Response({"error": "Username already exists"}, status=400)

    if User.objects.filter(email__iexact=email).first():
        return Response({"error": "Email already exists"}, status=400)

    # ✅ Hash password
    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    user = User(
        username=username,
        email=email.lower(),  # ✅ normalize email
        password=hashed_password,
        country=country,
        gender=gender,
        age=age
    )
    user.save()

    return Response(
        {
            "message": "User registered successfully",
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email
        },
        status=status.HTTP_201_CREATED
    )


# ================================
# ✅ LOGIN USER
# ================================
@swagger_auto_schema(
    method='post',
    operation_description="Login user",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'password'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=400
        )

    # ✅ FIX: Use filter + case insensitive
    user = User.objects.filter(email__iexact=email).first()

    if not user:
        return Response({"error": "Invalid email"}, status=404)

    # ✅ Ensure correct format
    stored_password = user.password
    if isinstance(stored_password, str):
        stored_password = stored_password.encode('utf-8')

    # ✅ Verify password
    if bcrypt.checkpw(password.encode('utf-8'), stored_password):
        return Response({
            "message": "Login successful",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "country": user.country,
                "gender": user.gender,
                "age": user.age
            }
        })

    return Response({"error": "Invalid password"}, status=400)


# ================================
# ✅ USER PROFILE
# ================================
@swagger_auto_schema(
    method='get',
    operation_description="Get user profile by email",
    manual_parameters=[
        openapi.Parameter(
            'email',
            openapi.IN_QUERY,
            description="User email",
            type=openapi.TYPE_STRING
        )
    ]
)
@api_view(['GET'])
@permission_classes([AllowAny])
def user_profile(request):
    email = request.GET.get('email')

    if not email:
        return Response({"error": "Email is required"}, status=400)

    user = User.objects.filter(email__iexact=email).first()

    if not user:
        return Response({"error": "User not found"}, status=404)

    return Response({
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "country": user.country,
        "gender": user.gender,
        "age": user.age
    })


# ================================
# ✅ FORGOT PASSWORD
# ================================
@swagger_auto_schema(
    method='post',
    operation_description="Forgot password",
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

    user = User.objects.filter(email__iexact=email).first()

    if not user:
        return Response({"error": "User not found"}, status=404)

    return Response({"message": "Password reset requested"})


# ================================
# ✅ RESET PASSWORD
# ================================
@swagger_auto_schema(
    method='post',
    operation_description="Reset password",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'new_password'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'new_password': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
)
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    email = request.data.get('email')
    new_password = request.data.get('new_password')

    user = User.objects.filter(email__iexact=email).first()

    if not user:
        return Response({"error": "User not found"}, status=404)

    hashed_password = bcrypt.hashpw(
        new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    user.password = hashed_password
    user.save()

    return Response({"message": "Password reset successful"})