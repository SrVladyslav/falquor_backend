from django.urls import path, include
from users.views import (
    RequestOTPView,
    VerifyOTPView,
    GetUserSessionViews,
    RevokeTokenView,
    ProfileViewSet,
    SessionRefreshTokenView,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"update", ProfileViewSet, basename="update")

urlpatterns = [
    # Auth / session endpoints (APIView-based)
    path("request-otp/", RequestOTPView.as_view(), name="request-otp"),
    path("login/", VerifyOTPView.as_view(), name="login"),
    path("session/", GetUserSessionViews.as_view(), name="session"),
    path("refresh/", SessionRefreshTokenView.as_view(), name="refresh-session"),
    path("logout/", RevokeTokenView.as_view(), name="logout"),
    # Mount the router URLs for the ProfileViewSet
    path("", include(router.urls)),
]
# urlpatterns = [
#     path("request-otp/", RequestOTPView.as_view(), name="request-otp"),
#     path("login/", VerifyOTPView.as_view(), name="login"),
#     path("session/", GetUserSessionViews.as_view(), name="session"),
#     path("refresh/", SessionRefreshTokenView.as_view(), name="refresh-session"),
#     path("logout/", RevokeTokenView.as_view(), name="logout"),
#     path("test/", ProfileView.as_view(), name="test"),
#     # Update account data
#     path("update/", ProfileView.as_view(), name="update-username"),
# ]
