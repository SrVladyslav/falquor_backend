from datetime import timedelta
from django.utils import timezone
import random


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def get_otp_expiry(minutes=5):
    return timezone.now() + timedelta(minutes=minutes)


def is_otp_valid(user, otp):
    return (
        user.otp_code == otp
        and user.otp_expires_at
        and user.otp_expires_at > timezone.now()
    )


def get_block_duration(tries: int) -> timedelta:
    """Return block duration based on failed attempts"""
    if tries < 3:
        return timedelta(seconds=0)
    elif tries == 3:
        return timedelta(minutes=1)
    elif tries == 4:
        return timedelta(minutes=5)
    elif tries == 5:
        return timedelta(minutes=10)
    else:
        return timedelta(minutes=15)
