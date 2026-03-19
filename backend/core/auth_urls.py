from django.urls import path

from . import auth_views

urlpatterns = [
    path("signup/", auth_views.signup, name="auth-signup"),
    path("login/", auth_views.login, name="auth-login"),
    path("logout/", auth_views.logout, name="auth-logout"),
    path("me/", auth_views.me, name="auth-me"),
]
