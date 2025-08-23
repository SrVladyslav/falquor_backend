import jwt
import secrets
from datetime import timedelta
from users.models import UserToken
from django.utils import timezone
from django.conf import settings
import hashlib
from users.models import Account
import json
from cryptography.fernet import Fernet


def generate_jwt(payload: dict, secret: str, expiry_minutes: int = 5):
    now = timezone.now()
    exp = now + timedelta(minutes=expiry_minutes)
    payload["exp"] = exp
    payload["iat"] = now
    token = jwt.encode(payload, secret, algorithm="HS256")
    return str(token), exp


def generate_sub_hash(user: Account):
    return hashlib.sha256(f"user-{user.uuid}-{user.jwt_secret}".encode()).hexdigest()


def encrypt_data_with_fernet(data: dict) -> str:
    fernet = Fernet(settings.SESSION_ENCRYPTION_KEY.encode())
    return fernet.encrypt(json.dumps(data).encode())


def decrypt_data_with_fernet(token: str) -> str:
    fernet = Fernet(settings.SESSION_ENCRYPTION_KEY.encode())
    return json.loads(fernet.decrypt(token.encode()).decode())


def create_token_pair(
    user, device: str = "", ip: str = "", user_agent: str = "", expiry_minutes: int = 15
) -> dict:
    sub_hash = generate_sub_hash(user)
    payload = {"sub": sub_hash}
    access_token, access_exp = generate_jwt(
        payload, user.jwt_secret, expiry_minutes=expiry_minutes
    )
    refresh_token = secrets.token_urlsafe(256)
    refresh_exp = timezone.now() + timedelta(days=7)

    print(f"Payload: {payload}")
    print(f"Access Token: {access_token}")
    print(f"Refresh Token: {refresh_token}")

    token = UserToken.objects.create(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
        device=device,
        user_agent=user_agent,
        ip_address=ip,
        expires_at=access_exp,
        refresh_expires_at=refresh_exp,
    )

    # Prepare the refresh token
    session_cookie_payload = {
        "refresh": str(refresh_token),
        "user_uuid": str(user.uuid),
        "email": user.email,
        "user_agent": user_agent,
    }
    session_cookie = encrypt_data_with_fernet(session_cookie_payload)

    return {
        "access": access_token,
        "refresh": refresh_token,
        "user_session": session_cookie,
        "expires_at": access_exp,
    }
