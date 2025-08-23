# core/middleware/origin_check.py

from django.conf import settings
from django.http import HttpResponseForbidden


class OriginCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = getattr(settings, "ALLOWED_ORIGINS", [""])

    def __call__(self, request):
        origin = request.headers.get("Origin")
        print(f"[DEBUG] Origin: {origin}")
        print(f"[DEBUG] Allowed Origins: {self.allowed_origins}")

        if origin and origin not in self.allowed_origins:
            return HttpResponseForbidden("Origin not allowed")

        return self.get_response(request)
