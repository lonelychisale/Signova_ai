from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django.conf import settings

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from bson.objectid import ObjectId
from functools import wraps

from .db import db
# from .ai_engine import SignAIEngine

import bcrypt
import jwt
import datetime
import traceback
import tempfile
import os

# ✅ safe whisper
try:
    import whisper
except:
    whisper = None

# ================= GLOBAL =================
users_col = db["users"]
blacklist_col = db["blacklist"]

# engine = SignAIEngine()
model = None
ACCESS_TOKEN_LIFETIME = datetime.timedelta(minutes=60)

# ================= TOKEN =================
def token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return Response(
                {"error": "Token missing"},
                status=401
            )

        try:
            # Supports:
            # Bearer token
            # OR raw token

            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            else:
                token = auth_header

            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )

            request.user_id = payload["user_id"]

        except jwt.ExpiredSignatureError:
            return Response(
                {"error": "Token expired"},
                status=401
            )

        except jwt.InvalidTokenError:
            return Response(
                {"error": "Invalid token"},
                status=401
            )

        except Exception as e:
            print(e)
            traceback.print_exc()

            return Response(
                {"error": "Authentication failed"},
                status=401
            )

        return view_func(request, *args, **kwargs)

    return wrapper

# ================= HEALTH =================
@swagger_auto_schema(method="get")
@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


# ================= REGISTER =================
register_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email", "password"],
    properties={
        "email": openapi.Schema(type=openapi.TYPE_STRING),
        "password": openapi.Schema(type=openapi.TYPE_STRING),
        "country": openapi.Schema(type=openapi.TYPE_STRING),
        "gender": openapi.Schema(type=openapi.TYPE_STRING),
        "age": openapi.Schema(type=openapi.TYPE_INTEGER),
    }
)

@swagger_auto_schema(method="post", request_body=register_schema)
@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    data = request.data

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return Response({"error": "Missing fields"}, status=400)

    if users_col.find_one({"email": email.lower()}):
        return Response({"error": "Email exists"}, status=400)

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    user = users_col.insert_one({
        "email": email.lower(),
        "password": hashed,
        "country": data.get("country"),
        "gender": data.get("gender"),
        "age": data.get("age"),
        "created_at": datetime.datetime.utcnow()
    })

    return Response({"user_id": str(user.inserted_id)})


# ================= LOGIN =================
login_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email", "password"],
    properties={
        "email": openapi.Schema(type=openapi.TYPE_STRING),
        "password": openapi.Schema(type=openapi.TYPE_STRING),
    }
)

@swagger_auto_schema(method="post", request_body=login_schema)
@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    email = request.data.get("email").lower()
    password = request.data.get("password")

    user = users_col.find_one({"email": email})

    if not user or not bcrypt.checkpw(password.encode(), user["password"]):
        return Response({"error": "Invalid credentials"}, status=401)

    token = jwt.encode(
        {
            "user_id": str(user["_id"]),
            "exp": datetime.datetime.utcnow() + ACCESS_TOKEN_LIFETIME,
        },
        settings.SECRET_KEY,
        algorithm="HS256"
    )

    return Response({"access_token": token})


# ================= RESET PASSWORD =================
reset_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email", "new_password"],
)

@swagger_auto_schema(method="post", request_body=reset_schema)
@api_view(["POST"])
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

    return Response({"message": "Password updated"})


# ================= PROFILE =================
@swagger_auto_schema(method="get", security=[{"Bearer": []}])
@api_view(["GET"])
@token_required
def user_profile(request):
    user = users_col.find_one({"_id": ObjectId(request.user_id)})

    return Response({
        "email": user.get("email"),
        "country": user.get("country"),
        "gender": user.get("gender"),
        "age": user.get("age"),
    })


# ================= LOGOUT =================
@swagger_auto_schema(method="post", security=[{"Bearer": []}])
@api_view(["POST"])
@token_required
def logout(request):
    token = request.headers.get("Authorization")

    blacklist_col.insert_one({"token": token})

    return Response({"message": "Logged out successfully"})


# # ================= TEXT → SIGN =================
# text_schema = openapi.Schema(
#     type=openapi.TYPE_OBJECT,
#     required=["text"]
# )

# @swagger_auto_schema(method="post", request_body=text_schema)
# @api_view(["POST"])
# def text_to_sign(request):
#     text = request.data.get("text")

#     videos = engine.convert(text)

#     urls = [
#         request.build_absolute_uri(f"/media/Signs/{v}")
#         for v in videos
#     ]

#     return Response({"text": text, "videos": urls})


# ================= WHISPER =================
@swagger_auto_schema(
    method="post",
    manual_parameters=[
        openapi.Parameter(
            "audio",
            openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=True
        )
    ],
    consumes=["multipart/form-data"]
)
@api_view(["POST"])
def whisper_transcribe(request):
    global model

    try:
        if whisper is None:
            return Response({"text": "Fallback: whisper unavailable"})

        if model is None:
            print("Loading Whisper model...")
            model = whisper.load_model("tiny")

        audio_file = request.FILES.get("audio")

        if not audio_file:
            return Response({"error": "Audio required"}, status=400)

        # ✅ limit size (important)
        if audio_file.size > 5 * 1024 * 1024:
            return Response({"error": "File too large"}, status=400)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            for chunk in audio_file.chunks():
                temp.write(chunk)
            path = temp.name

        result = model.transcribe(path, task="translate")
        text = result["text"]

        os.remove(path)

        return Response({"text": text})

    except Exception as e:
        traceback.print_exc()

        # ✅ SAFE fallback (prevents 502)
        return Response({
            "text": "Audio processed (fallback)",
            "error": str(e)
        })