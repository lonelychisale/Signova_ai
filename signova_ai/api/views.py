from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django.conf import settings

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from bson.objectid import ObjectId
from functools import wraps

from .db import db

import bcrypt
import jwt
import datetime
import traceback
import tempfile
import os

# =========================
# DATABASE
# =========================
users_col = db["users"]
blacklist_col = db["blacklist"]

# =========================
# GLOBALS
# =========================
ACCESS_TOKEN_LIFETIME = datetime.timedelta(minutes=60)
_whisper_model = None   # Lazy loaded


# =========================
# TOKEN DECORATOR
# =========================
def token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return Response({"error": "Token missing"}, status=401)

        try:
            token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else auth_header

            if blacklist_col.find_one({"token": token}):
                return Response({"error": "Token blacklisted"}, status=401)

            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            request.user_id = payload["user_id"]

        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)
        except Exception:
            return Response({"error": "Authentication failed"}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper


# =========================
# HEALTH CHECK
# =========================
@swagger_auto_schema(method="get")
@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


# =========================
# REGISTER
# =========================
@swagger_auto_schema(method="post", request_body=openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email", "password"],
    properties={
        "email": openapi.Schema(type=openapi.TYPE_STRING),
        "password": openapi.Schema(type=openapi.TYPE_STRING),
        "country": openapi.Schema(type=openapi.TYPE_STRING),
        "gender": openapi.Schema(type=openapi.TYPE_STRING),
        "age": openapi.Schema(type=openapi.TYPE_INTEGER),
    }
))
@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    try:
        data = request.data
        email = data.get("email", "").lower().strip()
        password = data.get("password")

        if not email or not password:
            return Response({"error": "Missing fields"}, status=400)

        if users_col.find_one({"email": email}):
            return Response({"error": "Email already exists"}, status=400)

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        user = users_col.insert_one({
            "email": email,
            "password": hashed,
            "country": data.get("country"),
            "gender": data.get("gender"),
            "age": data.get("age"),
            "created_at": datetime.datetime.utcnow()
        })

        return Response({
            "message": "User registered successfully",
            "user_id": str(user.inserted_id)
        })

    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


# =========================
# LOGIN
# =========================
@swagger_auto_schema(method="post", request_body=openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email", "password"],
    properties={
        "email": openapi.Schema(type=openapi.TYPE_STRING),
        "password": openapi.Schema(type=openapi.TYPE_STRING),
    }
))
@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    try:
        email = request.data.get("email", "").lower().strip()
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password required"}, status=400)

        user = users_col.find_one({"email": email})
        if not user or not bcrypt.checkpw(password.encode(), user["password"]):
            return Response({"error": "Invalid credentials"}, status=401)

        token = jwt.encode({
            "user_id": str(user["_id"]),
            "exp": datetime.datetime.utcnow() + ACCESS_TOKEN_LIFETIME,
        }, settings.SECRET_KEY, algorithm="HS256")

        return Response({"access_token": token})

    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


# =========================
# RESET PASSWORD
# =========================
@swagger_auto_schema(method="post", request_body=openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email", "new_password"],
    properties={
        "email": openapi.Schema(type=openapi.TYPE_STRING),
        "new_password": openapi.Schema(type=openapi.TYPE_STRING),
    }
))
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    try:
        email = request.data.get("email", "").lower().strip()
        new_password = request.data.get("new_password")

        if not email or not new_password:
            return Response({"error": "Email and new password required"}, status=400)

        user = users_col.find_one({"email": email})
        if not user:
            return Response({"error": "User not found"}, status=404)

        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())

        users_col.update_one({"_id": user["_id"]}, {"$set": {"password": hashed}})

        return Response({"message": "Password updated successfully"})

    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


# =========================
# PROFILE & LOGOUT (Shortened)
# =========================
@swagger_auto_schema(method="get", security=[{"Bearer": []}])
@api_view(["GET"])
@token_required
def user_profile(request):
    try:
        user = users_col.find_one({"_id": ObjectId(request.user_id)})
        if not user:
            return Response({"error": "User not found"}, status=404)

        return Response({
            "email": user.get("email"),
            "country": user.get("country"),
            "gender": user.get("gender"),
            "age": user.get("age"),
        })
    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


@swagger_auto_schema(method="post", security=[{"Bearer": []}])
@api_view(["POST"])
@token_required
def logout(request):
    try:
        auth_header = request.headers.get("Authorization")
        token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else auth_header

        blacklist_col.insert_one({
            "token": token,
            "created_at": datetime.datetime.utcnow()
        })
        return Response({"message": "Logged out successfully"})
    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


# =========================
# WHISPER TRANSCRIBE (Lazy Load)
# =========================
@swagger_auto_schema(
    method="post",
    manual_parameters=[openapi.Parameter("audio", openapi.IN_FORM, type=openapi.TYPE_FILE, required=True)],
    consumes=["multipart/form-data"]
)
@api_view(["POST"])
@permission_classes([AllowAny])
def whisper_transcribe(request):
    global _whisper_model

    try:
        audio_file = request.FILES.get("audio")
        if not audio_file:
            return Response({"error": "Audio file required"}, status=400)

        if audio_file.size > 5 * 1024 * 1024:
            return Response({"error": "File too large (max 5MB)"}, status=400)

        # Lazy load Whisper model only when first used
        if _whisper_model is None:
            print("🔵 Loading Faster Whisper model...")
            from faster_whisper import WhisperModel
            _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            print("✅ Whisper model loaded successfully")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            for chunk in audio_file.chunks():
                temp.write(chunk)
            temp_path = temp.name

        segments, _ = _whisper_model.transcribe(temp_path, task="translate")
        text = " ".join([segment.text for segment in segments])

        os.remove(temp_path)

        return Response({"text": text.strip()})

    except Exception as e:
        traceback.print_exc()
        return Response({"error": "Transcription failed"}, status=500)