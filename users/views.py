from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from django.utils import timezone
from users.models import Account
from users.utils.base import (
    generate_otp,
    is_otp_valid,
    get_otp_expiry,
    get_block_duration,
)
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from users.utils.crypto import create_token_pair, decrypt_data_with_fernet
from core.utils.base import is_valid_email
from django.conf import settings
from core.tasks.email_tasks import send_email
from users.models import UserToken
from rest_framework.permissions import IsAuthenticated
from users.serializers import UsernameUpdateSerializer, PreferencesUpdateSerializer


@method_decorator(
    ratelimit(key="ip", rate="1/10s", method="POST", block=True), name="post"
)
class RequestOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")
        print("Requesting for OTP for email: ", email)
        if not email:
            print("email is required")
            return Response({"error": "Email is required"}, status=400)

        if not is_valid_email(email):
            print("Invalid email")
            return Response({"error": "Invalid email"}, status=400)

        user, _ = Account.objects.get_or_create(email=email)
        print("user: ", user)
        otp = generate_otp()

        user.otp_code = otp
        user.otp_expires_at = get_otp_expiry()
        user.otp_tries = 0
        user.save()

        # Enviar el OTP por email/sms – ahora lo mostramos como prueba
        # send_email.delay(
        #     to_email=email,
        #     subject="Your OTP key",
        #     message=f"Your OTP key is {format_otp_code(otp)}.",
        # )
        print(f"[DEBUG] OTP for {email}: {otp}, expires at {user.otp_expires_at}")

        return Response(
            {
                "detail": "OTP sent",
            },
            status=200,
        )


@method_decorator(
    ratelimit(key="ip", rate="1/10s", method="POST", block=True), name="post"
)
class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not is_valid_email(email):
            return Response({"error": "Invalid email"}, status=400)

        try:
            user = Account.objects.get(email=email)
        except Account.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        if user.blocked_until and user.blocked_until > timezone.now():
            seconds_left = int((user.blocked_until - timezone.now()).total_seconds())
            return Response(
                {"error": f"You are blocked for {seconds_left // 60} min."},
                status=403,
            )

        # In case the user is blocked
        if not is_otp_valid(user, otp):
            user.otp_tries += 1

            if user.otp_tries >= settings.MAX_OTP_TRIES:
                duration = get_block_duration(user.otp_tries)
                user.blocked_until = timezone.now() + duration
                user.save()
                return Response(
                    {
                        "error": f"Too many failed attempts. Try again in {int(duration.total_seconds() // 60)} min."
                    },
                    status=403,
                )

            user.save()
            return Response(
                {
                    "error": "Invalid or expired OTP",
                    "tries": user.otp_tries,
                    "remaining": settings.MAX_OTP_TRIES - user.otp_tries,
                },
                status=400,
            )

        # OTP is valid
        user.otp_code = ""
        user.otp_tries = 0
        user.blocked_until = None
        user.save()

        # Issue a token (DRF Token)
        token_data = create_token_pair(
            user=user, expiry_minutes=settings.JWT_EXPIRY_MINUTES
        )

        return Response(
            {
                "access": token_data.get("access"),
                "refresh": token_data.get("user_session"),
            }
        )


# @method_decorator(
#     ratelimit(key="ip", rate="5/m", method="POST", block=True), name="post"
# )
class SessionRefreshTokenView(APIView):
    def post(self, request):
        user_session = request.headers.get("F-Session")
        print("User session: ", user_session)

        # Obtain the info
        try:
            data = decrypt_data_with_fernet(user_session)
        except Exception as _:
            return Response({"error": "Invalid session"}, status=400)
        print("Data: ", data, data.keys())
        # Check security
        refresh_token = data.get("refresh", None)
        email = data.get("email", None)
        user_agent = data.get("user_agent", None)

        user_token = UserToken.objects.filter(
            refresh_token=refresh_token,
            user__email=email,
            revoked=False,
            expires_at__gt=timezone.now(),
        ).first()

        if not user_token:
            return Response({"error": "Invalid session"}, status=400)

        user = user_token.user
        # OTP is valid
        user.otp_code = ""
        user.otp_tries = 0
        user.blocked_until = None
        user.save()

        # Revoke the token
        user_token.revoked = True
        user_token.save()

        # Issue a token (DRF Token)
        token_data = create_token_pair(
            user=user, expiry_minutes=settings.JWT_EXPIRY_MINUTES
        )

        print("Hola")
        return Response(
            {
                "access": token_data.get("access"),
                "user_session": token_data.get("user_session"),
            }
        )


class RevokeTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        mode = request.data.get("mode", "current")  # current, all, device
        token = request.auth
        user = request.user

        if mode == "current":
            revoked_count = UserToken.objects.filter(
                user=user, access_token=token
            ).update(revoked=True)
        elif mode == "all":
            revoked_count = UserToken.objects.filter(user=user, revoked=False).update(
                revoked=True
            )
        # elif mode == "device":
        #     device = request.data.get("device")
        #     if not device:
        #         return Response(
        #             {"error": "Device is required for 'device' mode"}, status=400
        #         )

        #     revoked_count = UserToken.objects.filter(
        #         user=user, device=device, revoked=False
        #     ).update(revoked=True)
        else:
            return Response({"error": "Invalid mode"}, status=400)

        return Response(
            {"detail": f"{revoked_count} token(s) revoked"},
            status=status.HTTP_200_OK,
        )


@method_decorator(
    ratelimit(key="ip", rate="5/10s", method="GET", block=True), name="get"
)
class GetUserSessionViews(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if selected_workspace := getattr(user, "selected_workspace", None):
            selected_workspace = selected_workspace.wid

        return Response(
            {
                "email": user.email,
                "username": user.username,
                # "uuid": user.uuid,
                "preferred_locale": user.preferred_locale,
                "icon_style": user.icon_style,
                "selected_workspace": getattr(user.selected_workspace, "wid", None),
                "is_active": user.is_active,
                "thumbnail": "https://imgs.search.brave.com/qFuGvnffqn2MBBFNlHdSCgE6Awxu65AwCD0SRK0j7N4/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly9pbWcu/ZnJlZXBpay5jb20v/ZnJlZS1waG90by9j/bG9zZS11cC1wb3J0/cmFpdC1iZWF1dGlm/dWwtY2F0XzIzLTIx/NDkyMTQ0MjAuanBn/P3NlbXQ9YWlzX2h5/YnJpZCZ3PTc0MA",
                # "thumbnail": "https://imgs.search.brave.com/hhidJa6b1fsO1EhcxGb395z-L5EKutVbml09Bv87xhA/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly9jZG4u/Y3JlYXRlLnZpc3Rh/LmNvbS9hcGkvbWVk/aWEvc21hbGwvMjUz/MDQ1NDk4L3N0b2Nr/LXBob3RvLXNtYWxs/LWN1dGUtY2F0LWp1/c3QtYXR0YWNr",
                "selected_workspace": selected_workspace,
                "permissons": (
                    user.permissions.values_list("code", flat=True)
                    if hasattr(user, "permissions")
                    else []
                ),
            }
        )


from rest_framework.permissions import IsAuthenticated
from core.tasks.email_tasks import send_email


class ProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        print("Sneging email")
        send_email.delay(
            to_email=request.user.email, subject="Prueba", message="Prueba"
        )

        return Response(
            {
                "email": request.user.email,
                "uuid": request.user.uuid,
            }
        )

    @action(detail=False, methods=["put"], url_path="username")
    def update_username(self, request):
        """
        Full/partial update of username (we only accept username for now).
        """
        user = request.user
        if not user.is_authenticated or not user.is_active:
            return Response(
                {"error": "User is inactive"},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = UsernameUpdateSerializer(data=request.data, context={"request": request})
        if not ser.is_valid():
            return Response(
                {"msg": "error-invalid-or-taken-username"},
                status=status.HTTP_409_CONFLICT,
            )

        user.username = ser.validated_data["username"]
        user.save(update_fields=["username"])

        return Response(
            {"email": user.email, "username": user.username},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["put"], url_path="preferences")
    def update_preferences(self, request):
        """
        Full/partial update of the preferreed language and/or icon styles.
        """
        user = request.user
        if not user.is_authenticated or not user.is_active:
            return Response(
                {"error": "User is inactive"},
                status=status.HTTP_403_FORBIDDEN,
            )

        print("DATA: ", request.data)
        ser = PreferencesUpdateSerializer(
            instance=request.user,
            data=request.data,
            partial=True,  # allow sending one or both fields
            context={"request": request},
        )
        if not ser.is_valid():
            return Response(
                {"msg": "error-invalid-data"},
                status=status.HTTP_409_CONFLICT,
            )

        # Apply changes to the user account
        ser.save()

        return Response(
            {
                "language": request.user.preferred_locale,
                "icon_style": request.user.icon_style,
            },
            status=status.HTTP_200_OK,
        )
