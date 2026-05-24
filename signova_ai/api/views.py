from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.mail import send_mail

from .db import db

import bcrypt
import jwt
import datetime
import os
import random
import traceback
import uuid

from bson.objectid import ObjectId
from functools import wraps

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .ai_engine import SignAIEngine

from dotenv import load_dotenv
from openai import OpenAI


import whisper

#  Load model once (important!)
model = whisper.load_model("tiny")



load_dotenv()


# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import AllowAny
# from rest_framework.response import Response
# from django.core.mail import send_mail
# from django.conf import settings

# from .db import db

# import bcrypt
# import jwt
# import datetime
# import os
# import random
# import traceback

# from bson.objectid import ObjectId
# from functools import wraps

# from drf_yasg.utils import swagger_auto_schema
# from drf_yasg import openapi

# from .ai_engine import SignAIEngine

# from dotenv import load_dotenv

# load_dotenv()

# #  CONFIG

SECRET_KEY = os.getenv("SECRET_KEY") or "fallback_secret_key"

ACCESS_TOKEN_LIFETIME = datetime.timedelta(minutes=60)
REFRESH_TOKEN_LIFETIME = datetime.timedelta(days=7)

users_col = db["users"]
blacklist_col = db["blacklist"]
reset_tokens_col = db["password_reset_tokens"]
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#  TOKEN DECORATOR


def token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
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
        except Exception:
            return Response({"error": "Invalid token"}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper


#  REGISTER


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["username", "email", "password"],
        properties={
            "username": openapi.Schema(type=openapi.TYPE_STRING),
            "email": openapi.Schema(type=openapi.TYPE_STRING),
            "password": openapi.Schema(type=openapi.TYPE_STRING),
            "country": openapi.Schema(type=openapi.TYPE_STRING),
            "gender": openapi.Schema(type=openapi.TYPE_STRING),
            "age": openapi.Schema(type=openapi.TYPE_INTEGER),
        },
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
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

        return Response(
            {
                "user_id": str(result.inserted_id),
                "message": "User registered successfully",
            }
        )

    except Exception as e:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


#  LOGIN


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email", "password"],
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING),
            "password": openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
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

        return Response({"access_token": access_token, "refresh_token": refresh_token})

    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


#  REQUEST PASSWORD RESET


@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email"],
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
def request_password_reset(request):
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
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({"message": "Reset code sent successfully"})

    except Exception as e:
        traceback.print_exc()
        return Response({"error": "Email failed", "details": str(e)}, status=500)






#  RESET PASSWORD


reset_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email", "new_password"],
    properties={
        "email": openapi.Schema(type=openapi.TYPE_STRING),
        "new_password": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

@swagger_auto_schema(
    method="post",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["token", "new_password"],
        properties={
            "token": openapi.Schema(type=openapi.TYPE_STRING),
            "new_password": openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
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

        return Response({"message": "Password reset successful"})

    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)



# ================= RESET PASSWORD =================

@swagger_auto_schema(method="post", request_body=reset_schema)
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    try:
        email = request.data.get("email")
        new_password = request.data.get("new_password")

        user = users_col.find_one({"email": email})

        if not user:
            return Response({"error": "User not found"}, status=404)

        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())

        users_col.update_one(
            {"_id": user["_id"]}, {"$set": {"password": hashed}}
        )

        return Response({"message": "Password updated"})

    except Exception:
        traceback.print_exc()
        return Response({"error": "Server error"}, status=500)



#  PROFILE


@swagger_auto_schema(method="get", security=[{"Bearer": []}])
@api_view(["GET"])
@token_required
def user_profile(request):
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

    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


#  LOGOUT


@swagger_auto_schema(method="post", security=[{"Bearer": []}])
@api_view(["POST"])
@token_required
def logout(request):
    try:
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return Response({"error": "Authorization header missing"}, status=400)

        token = (
            auth_header.split()[1] if auth_header.startswith("Bearer ") else auth_header
        )

        if not blacklist_col.find_one({"token": token}):
            blacklist_col.insert_one(
                {"token": token, "created_at": datetime.datetime.utcnow()}
            )

        return Response({"message": "Logged out successfully"})

    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


#  AI

engine = SignAIEngine()

text_to_sign_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["text"],
    properties={
        "text": openapi.Schema(type=openapi.TYPE_STRING),
    },
)


@swagger_auto_schema(method="post", request_body=text_to_sign_schema)
# @api_view(["POST"])
# def text_to_sign(request):
#     try:
#         text = request.data.get("text")

#         if not text:
#             return Response({"error": "Text required"}, status=400)

#         return Response({"input_text": text, "sign_videos": engine.convert(text)})

#     except Exception:
#         traceback.print_exc()
#         return Response({"error": "Internal server error"}, status=500)
@api_view(["POST"])
def text_to_sign(request):
    try:
        text = request.data.get("text")

        if not text:
            return Response({"error": "Text required"}, status=400)

        videos = engine.convert(text)  # ["hello.mp4", "world.mp4"]

        video_urls = [
            request.build_absolute_uri(f"/media/Signs/{video}")
            for video in videos
        ]

        return Response({
            "input_text": text,
            "sign_videos": video_urls
        })

    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)





import whisper
import tempfile
import os
import traceback

#  Load model once (important)
model = whisper.load_model("tiny")

@swagger_auto_schema(
    method="post",
    manual_parameters=[
        openapi.Parameter(
            name="audio",
            in_=openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=True,
            description="Upload audio file (.wav, .mp3)"
        ),
        openapi.Parameter(
            name="lang",
            in_=openapi.IN_FORM,
            type=openapi.TYPE_STRING,
            required=False,
            description="Target language (optional)"
        ),
    ],
    consumes=["multipart/form-data"],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def whisper_transcribe(request):
    try:
        #  Get uploaded file
        audio_file = request.FILES.get("audio")
        lang = request.data.get("lang")

        if not audio_file:
            return Response({"error": "Audio file is required"}, status=400)
       
        #  Save safely using temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            for chunk in audio_file.chunks():
                temp_file.write(chunk)

            temp_path = temp_file.name

        print(" File saved at:", temp_path)

        #  Transcribe (FREE local whisper)
        result = model.transcribe(temp_path)
        text = result["text"]

        #  Optional translation
        translated = None
        if lang:
            result_translate = model.transcribe(temp_path, task="translate")
            translated = result_translate["text"]

        #  Clean up
        os.remove(temp_path)

        return Response({
            "text": text,
            "translated": translated
        })

    except Exception as e:
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)