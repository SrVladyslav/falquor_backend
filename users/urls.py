from django.urls import path
from users.views import (
    RequestOTPView,
    VerifyOTPView,
    GetUserSessionViews,
    RevokeTokenView,
    ProfileView,
    SessionRefreshTokenView,
)

urlpatterns = [
    path("request-otp/", RequestOTPView.as_view(), name="request-otp"),
    path("login/", VerifyOTPView.as_view(), name="login"),
    path("session/", GetUserSessionViews.as_view(), name="session"),
    path("refresh/", SessionRefreshTokenView.as_view(), name="refresh-session"),
    path("logout/", RevokeTokenView.as_view(), name="logout"),
    path("test/", ProfileView.as_view(), name="test"),
]
