from django.urls import path
from .views import (
    register_user,
    user_profile,
    forgot_password,
    reset_password
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [

    path('register/', register_user),

    path('login/', TokenObtainPairView.as_view()),

    path('token/refresh/', TokenRefreshView.as_view()),

    path('profile/', user_profile),

    path('forgot-password/', forgot_password),

    path('reset-password/', reset_password),
]