from rest_framework.authentication import SessionAuthentication


class CsrfEnforcedSessionAuthentication(SessionAuthentication):
    """Session auth that enforces CSRF for every unsafe request, including anonymous ones.

    DRF's default only checks CSRF for authenticated sessions; anonymous carts and
    guest checkout must be protected as well.
    """

    def authenticate(self, request):
        user_auth = super().authenticate(request)
        if user_auth is None and request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            self.enforce_csrf(request)
        return user_auth
