from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import tempfile
from ai.predict import predict_sign

from django.conf import settings

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from bson.objectid import ObjectId
from functools import wraps

from .db import db
import requests
import bcrypt
import jwt
import datetime
import traceback
import os

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# =========================
# DATABASE
# =========================
users_col = db["users"]
blacklist_col = db["blacklist"]

# =========================
# CONFIG
# =========================
ACCESS_TOKEN_LIFETIME = datetime.timedelta(minutes=60)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


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
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})


# =========================
# REGISTER
# =========================
@swagger_auto_schema(method="post", request_body=openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email", "password"],
    properties={
        "fullname": openapi.Schema(type=openapi.TYPE_STRING),
        "email": openapi.Schema(type=openapi.TYPE_STRING),
        "password": openapi.Schema(type=openapi.TYPE_STRING),
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
            "fullname": data.get("fullname"),
            "email": email,
            "password": hashed,
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


#google auth
google_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["token"],
    properties={
        "token": openapi.Schema(
            type=openapi.TYPE_STRING
        )
    }
)
# =========================
# GOOGLE AUTH (ALL PLATFORMS)
# =========================

google_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["token"],
    properties={
        "token": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Google ID token"
        ),
    }
)

@swagger_auto_schema(
    method="post",
    request_body=google_schema
)
@api_view(["POST"])
@permission_classes([AllowAny])
def google_auth(request):

    try:
        google_token = request.data.get("token")

        if not google_token:
            return Response(
                {"error": "Google token required"},
                status=400
            )

        # =====================================
        # VERIFY TOKEN WITHOUT CLIENT ID
        # WORKS FOR:
        # - Android
        # - iOS
        # - Web
        # - Flutter
        # =====================================

        idinfo = id_token.verify_oauth2_token(
            google_token,
            google_requests.Request()
        )

        # Optional checks
        issuer = idinfo.get("iss")

        if issuer not in [
            "accounts.google.com",
            "https://accounts.google.com"
        ]:
            return Response(
                {"error": "Invalid token issuer"},
                status=401
            )

        email = idinfo.get("email")
        fullname = idinfo.get("name")
        picture = idinfo.get("picture")

        if not email:
            return Response(
                {"error": "Invalid Google account"},
                status=400
            )

        email = email.lower()

        # =====================================
        # CHECK USER
        # =====================================

        user = users_col.find_one({
            "email": email
        })

        # =====================================
        # CREATE USER
        # =====================================

        if not user:

            user_data = {
                "fullname": fullname,
                "email": email,
                "picture": picture,
                "google_auth": True,
                "created_at": datetime.datetime.utcnow()
            }

            inserted = users_col.insert_one(user_data)

            user = users_col.find_one({
                "_id": inserted.inserted_id
            })

        # =====================================
        # GENERATE JWT
        # =====================================

        access_token = jwt.encode(
            {
                "user_id": str(user["_id"]),
                "email": user["email"],
                "exp": datetime.datetime.utcnow()
                + ACCESS_TOKEN_LIFETIME,
            },
            settings.SECRET_KEY,
            algorithm="HS256"
        )

        # =====================================
        # RESPONSE
        # =====================================

        return Response({
            "message": "Google login successful",
            "access_token": access_token,
            "user": {
                "id": str(user["_id"]),
                "email": user.get("email"),
                "fullname": user.get("fullname"),
                "picture": user.get("picture"),
            }
        })

    except ValueError:
        return Response(
            {"error": "Invalid Google token"},
            status=401
        )

    except Exception as e:
        traceback.print_exc()

        return Response(
            {"error": str(e)},
            status=500
        )


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

        users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"password": hashed}}
        )

        return Response({"message": "Password updated successfully"})

    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


# =========================
# PROFILE
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
            "fullname": user.get("fullname"),
            "email": user.get("email"),
        })
    except Exception:
        traceback.print_exc()
        return Response({"error": "Internal server error"}, status=500)


# =========================
# LOGOUT
# =========================
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
# SPEECH TO TEXT - GROQ WHISPER
# =========================
@swagger_auto_schema(
    method="post",
    manual_parameters=[openapi.Parameter("audio", openapi.IN_FORM, type=openapi.TYPE_FILE, required=True)],
    consumes=["multipart/form-data"]
)
@api_view(["POST"])
@permission_classes([AllowAny])
def whisper_transcribe(request):
    try:
        if not GROQ_API_KEY:
            return Response({"error": "Groq API Key not configured. Please check your .env file."}, status=500)

        audio_file = request.FILES.get("audio")
        if not audio_file:
            return Response({"error": "Audio file required"}, status=400)

        if audio_file.size > 25 * 1024 * 1024:
            return Response({"error": "File too large (max 25MB)"}, status=400)

        audio_bytes = audio_file.read()

        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

        response = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers=headers,
            files=files,
            data={"model": "whisper-large-v3-turbo", "response_format": "json"},
            timeout=60
        )

        if response.status_code != 200:
            return Response({
                "error": "Groq API Error",
                "details": response.text
            }, status=response.status_code)

        result = response.json()
        return Response({
            "text": result.get("text", "").strip()
        })

    except Exception as e:
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)




# =========================
#PREDICT_sIGN SWAGGER SCHEMA
# =========================
predict_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["coordinates"],
    properties={
        "coordinates": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(
                type=openapi.TYPE_NUMBER
            ),
            description="Array of 63 hand landmark values"
        )
    }
)

# =========================
# PREDICT SIGN API
# =========================
@swagger_auto_schema(
    method="post",
    request_body=predict_schema,
    operation_summary="Predict Sign Language",
    operation_description="""
Send 63 MediaPipe hand landmark coordinates
to predict the sign language letter.

Example:
[x1, y1, z1, x2, y2, z2, ...]
""",
    responses={
        200: openapi.Response(
            description="Prediction successful"
        ),
        400: "Bad Request",
        500: "Internal Server Error"
    }
)
@api_view(["POST"])
@permission_classes([AllowAny])
def predict_sign_api(request):

    try:

        coordinates = request.data.get("coordinates")

        # =========================
        # VALIDATION
        # =========================
        if not coordinates:

            return Response(
                {
                    "error": "Coordinates required"
                },
                status=400
            )

        if not isinstance(coordinates, list):

            return Response(
                {
                    "error": "Coordinates must be a list"
                },
                status=400
            )

        if len(coordinates) != 63:

            return Response(
                {
                    "error": "Exactly 63 coordinate values required"
                },
                status=400
            )

        # =========================
        # PREDICTION
        # =========================
        prediction = predict_sign(
            coordinates
        )

        # =========================
        # RESPONSE
        # =========================
        return Response({
            "success": True,
            "prediction": prediction
        })

    except Exception as e:

        return Response(
            {
                "success": False,
                "error": str(e)
            },
            status=500
        )

