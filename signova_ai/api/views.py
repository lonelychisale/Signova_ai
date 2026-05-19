from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings

from .db import db

import bcrypt
import jwt
import datetime
import os
import random
import traceback

from bson.objectid import ObjectId
from functools import wraps

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .ai_engine import SignAIEngine

from dotenv import load_dotenv

load_dotenv()

#  CONFIG

SECRET_KEY = os.getenv("SECRET_KEY") or "fallback_secret_key"

ACCESS_TOKEN_LIFETIME = datetime.timedelta(minutes=60)
REFRESH_TOKEN_LIFETIME = datetime.timedelta(days=7)

users_col = db["users"]
blacklist_col = db["blacklist"]
reset_tokens_col = db["password_reset_tokens"]

#  TOKEN DECORATOR


def token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        print(" TOKEN CHECK")

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return Response({"error": "Token missing"}, status=401)

        try:
            token = (
                auth_header.split()[1]
                if auth_header.startswith("Bearer ")
                else auth_header
            )

            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], leeway=30)

            if payload.get("type") != "access":
                return Response({"error": "Use access token"}, status=401)

            if blacklist_col.find_one({"token": token}):
                return Response({"error": "Token blacklisted"}, status=401)

            request.user_id = payload["user_id"]

        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=401)
        except Exception as e:
            print(" TOKEN ERROR:", str(e))
            return Response({"error": "Invalid token"}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper


#  REGISTER


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["username", "email", "password"],
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    print(" REGISTER")

    try:
        data = request.data

        if not all([data.get("username"), data.get("email"), data.get("password")]):
            return Response({"error": "Missing required fields"}, status=400)

        email = data["email"].lower()

        if users_col.find_one({"email": email}):
            return Response({"error": "Email exists"}, status=400)

        hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt())

        result = users_col.insert_one(
            {
                "username": data["username"],
                "email": email,
                "password": hashed,
                "country": data.get("country"),
                "gender": data.get("gender"),
                "age": data.get("age"),
            }
        )

        print(" User created")

        return Response(
            {
                "user_id": str(result.inserted_id),
                "message": "User registered successfully",
            }
        )

    except Exception as e:
        print(" REGISTER ERROR:", str(e))
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


#  LOGIN


@swagger_auto_schema(method="post")
@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    print(" LOGIN")

    try:
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password required"}, status=400)

        email = email.lower()
        user = users_col.find_one({"email": email})

        if not user:
            return Response({"error": "Invalid credentials"}, status=401)

        if not bcrypt.checkpw(password.encode(), user["password"]):
            return Response({"error": "Invalid credentials"}, status=401)

        access_token = jwt.encode(
            {
                "user_id": str(user["_id"]),
                "type": "access",
                "exp": datetime.datetime.utcnow() + ACCESS_TOKEN_LIFETIME,
            },
            SECRET_KEY,
            algorithm="HS256",
        )

        refresh_token = jwt.encode(
            {
                "user_id": str(user["_id"]),
                "type": "refresh",
                "exp": datetime.datetime.utcnow() + REFRESH_TOKEN_LIFETIME,
            },
            SECRET_KEY,
            algorithm="HS256",
        )

        print(" Login success")

        return Response({"access_token": access_token, "refresh_token": refresh_token})

    except Exception as e:
        print(" LOGIN ERROR:", str(e))
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


#  REQUEST PASSWORD RESET


@swagger_auto_schema(method="post")
@api_view(["POST"])
@permission_classes([AllowAny])
def request_password_reset(request):
    print(" PASSWORD RESET")

    try:
        email = request.data.get("email")

        if not email:
            return Response({"error": "Email required"}, status=400)

        email = email.lower()
        user = users_col.find_one({"email": email})

        if not user:
            return Response(
                {"message": "If an account exists, a reset code has been sent"}
            )

        otp = str(random.randint(100000, 999999))
        print(" OTP:", otp)

        reset_tokens_col.insert_one(
            {
                "user_id": str(user["_id"]),
                "token": otp,
                "used": False,
                "expires_at": datetime.datetime.utcnow()
                + datetime.timedelta(minutes=10),
            }
        )

        send_mail(
            subject="Password Reset Code",
            message=f"Your reset code is: {otp}",
            from_email=settings.EMAIL_HOST_USER,  #  FIXED
            recipient_list=[email],
            fail_silently=False,
        )

        print(" Email sent")

        return Response({"message": "Reset code sent successfully"})

    except Exception as e:
        print(" RESET ERROR:", str(e))
        traceback.print_exc()
        return Response({"error": "Email failed", "details": str(e)}, status=500)


#  RESET PASSWORD


@swagger_auto_schema(method="post")
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    print(" RESET PASSWORD")

    try:
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not token or not new_password:
            return Response({"error": "Token and password required"}, status=400)

        token_data = reset_tokens_col.find_one({"token": token})

        if not token_data:
            return Response({"error": "Invalid code"}, status=400)

        if token_data.get("used"):
            return Response({"error": "Code already used"}, status=400)

        if token_data["expires_at"] < datetime.datetime.utcnow():
            return Response({"error": "Code expired"}, status=400)

        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())

        users_col.update_one(
            {"_id": ObjectId(token_data["user_id"])}, {"$set": {"password": hashed}}
        )

        reset_tokens_col.update_one({"token": token}, {"$set": {"used": True}})

        print(" Password updated")

        return Response({"message": "Password reset successful"})

    except Exception as e:
        print(" RESET PASSWORD ERROR:", str(e))
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


#  PROFILE


@swagger_auto_schema(method="get", security=[{"Bearer": []}])
@api_view(["GET"])
@token_required
def user_profile(request):
    print(" PROFILE")

    try:
        user = users_col.find_one({"_id": ObjectId(request.user_id)})

        if not user:
            return Response({"error": "User not found"}, status=404)

        return Response(
            {
                "username": user.get("username"),
                "email": user.get("email"),
                "country": user.get("country"),
                "gender": user.get("gender"),
                "age": user.get("age"),
            }
        )

    except Exception as e:
        print(" PROFILE ERROR:", str(e))
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


#  LOGOUT


@swagger_auto_schema(method="post", security=[{"Bearer": []}])
@api_view(["POST"])
@token_required
def logout(request):
    print(" LOGOUT")

    try:
        auth_header = request.headers.get("Authorization")

        token = (
            auth_header.split()[1] if auth_header.startswith("Bearer ") else auth_header
        )

        if not blacklist_col.find_one({"token": token}):
            blacklist_col.insert_one(
                {"token": token, "created_at": datetime.datetime.utcnow()}
            )

        return Response({"message": "Logged out successfully"})

    except Exception as e:
        print(" LOGOUT ERROR:", str(e))
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


#  AI

engine = SignAIEngine()


@swagger_auto_schema(method="post")
@api_view(["POST"])
def text_to_sign(request):
    print(" AI REQUEST")

    try:
        text = request.data.get("text")

        if not text:
            return Response({"error": "Text required"}, status=400)

        return Response({"input_text": text, "sign_videos": engine.convert(text)})

    except Exception as e:
        print(" AI ERROR:", str(e))
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)
