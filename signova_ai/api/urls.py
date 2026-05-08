from django.urls import path

from .views import (
    register_user,
    login_user,          # ✅ IMPORTANT: use your custom login
    user_profile,
    forgot_password,
    reset_password
)

from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [

    # ✅ REGISTER
    path('register/', register_user, name='register'),

    # ✅ LOGIN (MongoDB + bcrypt + your model)
    path('login/', login_user, name='login'),

    # ✅ REFRESH TOKEN (keep this)
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ✅ PROFILE
    path('profile/', user_profile, name='profile'),

    # ✅ PASSWORD RESET
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/', reset_password, name='reset_password'),

]