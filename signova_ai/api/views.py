from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .db import db

import bcrypt
import jwt
import datetime
import os

from bson.objectid import ObjectId
from functools import wraps

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from dotenv import load_dotenv
load_dotenv()



#  CONFIG

SECRET_KEY = os.getenv("SECRET_KEY") or "fallback_secret_key"

ACCESS_TOKEN_LIFETIME = datetime.timedelta(minutes=60)
REFRESH_TOKEN_LIFETIME = datetime.timedelta(days=7)

users_col = db["users"]
blacklist_col = db["blacklist"]



#  TOKEN DECORATOR 

def token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return Response({"error": "Token missing"}, status=401)

        try:
            #  Works with Swagger + Postman
            if auth_header.startswith("Bearer "):
                token = auth_header.split()[1]
            else:
                token = auth_header.strip()

            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=["HS256"],
                leeway=30
            )

            if payload.get("type") != "access":
                return Response({"error": "Use access token"}, status=401)

            if blacklist_col.find_one({"token": token}):
                return Response({"error": "Token blacklisted"}, status=401)

            request.user_id = payload["user_id"]

        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=401)

        except Exception as e:
            return Response({"error": "Invalid token", "details": str(e)}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper



#  REGISTER
@swagger_auto_schema(
    method='post',
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
    data = request.data

    if not all([data.get('username'), data.get('email'), data.get('password')]):
        return Response({"error": "Missing required fields"}, status=400)

    if users_col.find_one({"email": data['email'].lower()}):
        return Response({"error": "Email exists"}, status=400)

    hashed = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt())

    user_data = {
        "username": data['username'],
        "email": data['email'].lower(),
        "password": hashed,
        "country": data.get('country'),
        "gender": data.get('gender'),
        "age": data.get('age'),
    }

    result = users_col.insert_one(user_data)

    return Response({
        "user_id": str(result.inserted_id),
        "message": "User registered successfully"
    })



#LOGIN
@swagger_auto_schema(
    method='post',
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
    email = request.data.get("email")
    password = request.data.get("password")

    user = users_col.find_one({"email": email.lower()})

    if not user:
        return Response({"error": "Invalid email"}, status=404)

    if not bcrypt.checkpw(password.encode(), user["password"]):
        return Response({"error": "Invalid password"}, status=400)

    access_token = jwt.encode({
        "user_id": str(user["_id"]),
        "type": "access",
        "exp": datetime.datetime.utcnow() + ACCESS_TOKEN_LIFETIME
    }, SECRET_KEY, algorithm="HS256")

    refresh_token = jwt.encode({
        "user_id": str(user["_id"]),
        "type": "refresh",
        "exp": datetime.datetime.utcnow() + REFRESH_TOKEN_LIFETIME
    }, SECRET_KEY, algorithm="HS256")

    
    if isinstance(access_token, bytes):
        access_token = access_token.decode()

    if isinstance(refresh_token, bytes):
        refresh_token = refresh_token.decode()

    return Response({
        "access_token": access_token,
        "refresh_token": refresh_token
    })



#  REFRESH TOKEN 
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['refresh_token'],
        properties={
            'refresh_token': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
)
@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_access_token(request):
    token = request.data.get("refresh_token")

    if not token:
        return Response({"error": "Refresh token required"}, status=400)

    try:
        payload = jwt.decode(
            token.strip(),
            SECRET_KEY,
            algorithms=["HS256"],
            leeway=30
        )

        if payload.get("type") != "refresh":
            return Response({"error": "Invalid token type"}, status=401)

        new_access = jwt.encode({
            "user_id": payload["user_id"],
            "type": "access",
            "exp": datetime.datetime.utcnow() + ACCESS_TOKEN_LIFETIME
        }, SECRET_KEY, algorithm="HS256")

        if isinstance(new_access, bytes):
            new_access = new_access.decode()

        return Response({"access_token": new_access})

    except jwt.ExpiredSignatureError:
        return Response({"error": "Refresh token expired"}, status=401)

    except Exception as e:
        return Response({"error": "Invalid refresh token", "details": str(e)}, status=401)



#  PROFILE
@swagger_auto_schema(method='get', security=[{'Bearer': []}])
@api_view(['GET'])
@token_required
def user_profile(request):
    user = users_col.find_one({"_id": ObjectId(request.user_id)})

    if not user:
        return Response({"error": "User not found"}, status=404)

    return Response({
        "username": user["username"],
        "email": user["email"],
        "country": user.get("country"),
        "gender": user.get("gender"),
        "age": user.get("age"),
    })


#  LOGOUT

@swagger_auto_schema(method='post', security=[{'Bearer': []}])
@api_view(['POST'])
@token_required
def logout(request):
    auth_header = request.headers.get("Authorization")

    if auth_header.startswith("Bearer "):
        token = auth_header.split()[1]
    else:
        token = auth_header.strip()

    if not blacklist_col.find_one({"token": token}):
        blacklist_col.insert_one({
            "token": token,
            "created_at": datetime.datetime.utcnow()
        })

    return Response({"message": "Logged out successfully"})



#  RESET PASSWORD
@swagger_auto_schema(
    method='post',
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
    email = request.data.get("email")
    new_password = request.data.get("new_password")

    user = users_col.find_one({"email": email.lower()})

    if not user:
        return Response({"error": "User not found"}, status=404)

    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())

    users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": hashed}}
    )

    return Response({"message": "Password reset successful"})
