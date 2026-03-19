from django.conf import settings
from rest_framework.authentication import TokenAuthentication


class CookieTokenAuthentication(TokenAuthentication):
    """Read the DRF token from an HTTP-only cookie instead of the Authorization header."""

    def authenticate(self, request):
        token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        if not token:
            return None
        return self.authenticate_credentials(token)
