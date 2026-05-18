from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_user),
    path('login/', views.login_user),
    path('refresh/', views.refresh_access_token),
    path('profile/', views.user_profile),
    path('logout/', views.logout),
    path('reset-password/', views.reset_password),
]