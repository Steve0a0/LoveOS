import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Profile
from .serializers import LoginSerializer, SignupSerializer, UserSerializer

logger = logging.getLogger("loveos.audit")

User = get_user_model()


def _set_auth_cookie(response, token_key):
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token_key,
        max_age=settings.AUTH_COOKIE_MAX_AGE,
        httponly=settings.AUTH_COOKIE_HTTPONLY,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/",
    )


def _clear_auth_cookie(response):
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = User.objects.create_user(
        username=serializer.validated_data["email"],
        email=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
    )
    Profile.objects.create(
        user=user,
        display_name=serializer.validated_data["display_name"],
    )

    token, _ = Token.objects.get_or_create(user=user)
    response = Response(
        UserSerializer(user).data,
        status=status.HTTP_201_CREATED,
    )
    _set_auth_cookie(response, token.key)
    logger.info("auth.signup user=%s email=%s", user.pk, user.email)
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = authenticate(
        request,
        username=serializer.validated_data["email"].lower(),
        password=serializer.validated_data["password"],
    )
    if user is None:
        logger.warning("auth.login_failed email=%s", serializer.validated_data["email"])
        return Response(
            {"detail": "Invalid email or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)
    response = Response(UserSerializer(user).data)
    _set_auth_cookie(response, token.key)
    logger.info("auth.login user=%s", user.pk)
    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    # Delete the token so it can't be reused
    logger.info("auth.logout user=%s", request.user.pk)
    Token.objects.filter(user=request.user).delete()
    response = Response({"detail": "Logged out."})
    _clear_auth_cookie(response)
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)
