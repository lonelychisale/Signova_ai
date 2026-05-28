from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_user),
    path("login/", views.login_user),
     path("google/", views.google_auth),
    # path('refresh/', views.refresh_access_token),
    path("profile/", views.user_profile),
    path("logout/", views.logout),
    # path("request-password-reset/", views.request_password_reset),
    path("reset-password/", views.reset_password),
    path("speech-to-text/", views.whisper_transcribe),
    path("predict-sign/", views.predict_sign_api),
    # path("text-to-sign/", views.text_to_sign),
]
