from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, time, date
import pytz
from django.core.validators import RegexValidator
import re

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r"^#([0-9A-Fa-f]{6})$",
    message="Color must be a hex code like #112233 (6 hex digits).",
)


def obfuscate_email(email: str, visible: int = 3) -> str:
    """
    Obfuscates part of the email address, showing only the first `visible` characters
    before the @ symbol. For example: 'mic***@domain.com'
    """
    if not email or "@" not in email:
        return ""

    local_part, domain = email.split("@", 1)
    if len(local_part) <= visible:
        obfuscated = local_part[0] + "*" * (len(local_part) - 1)
    else:
        obfuscated = local_part[:visible] + "*" * (len(local_part) - visible)

    return f"{obfuscated}@{domain}"


def format_otp_code(otp_code: str) -> str:
    return f"{otp_code[:3]}-{otp_code[3:6]}"


def is_valid_email(email: str) -> bool:
    """Validates if a given string is a valid email or not."""
    validator = EmailValidator()
    try:
        validator(email)
        return True
    except ValidationError:
        return False


def current_time() -> time:
    """Return current time in UTC as a time object (no date)."""
    return timezone.now().time()


def get_local_time(
    value: datetime | time = timezone.now(), tz: str | pytz.BaseTzInfo = "Europe/Madrid"
) -> datetime:
    """
    Convert a UTC datetime or time object into the specified local timezone.

    Args:
        value (datetime | time):
            - A timezone-aware datetime in UTC, or
            - A naive datetime (assumed UTC), or
            - A time object (treated as UTC time).
        tz (str | pytz timezone):
            - IANA timezone string (e.g., "Europe/Madrid"), OR
            - pytz timezone object (e.g., pytz.timezone("Europe/Madrid"))

    Returns:
        datetime | time:
            - If input is datetime, returns a localized datetime.
            - If input is time, returns a localized time.

    Example:
        >>> from django.utils import timezone
        >>> dt = timezone.now()  # UTC datetime
        >>> get_local_time(dt, "Europe/Madrid")
        datetime.datetime(2025, 8, 17, 19, 36, tzinfo=<DstTzInfo 'Europe/Madrid' CEST+2:00:00 DST>)

        >>> tz = pytz.timezone("Europe/Madrid")
        >>> get_local_time(dt, tz)
        datetime.datetime(2025, 8, 17, 19, 36, tzinfo=<DstTzInfo 'Europe/Madrid' CEST+2:00:00 DST>)

        >>> t = time(15, 30)  # 15:30 UTC
        >>> get_local_time(t, "Europe/Madrid")
        datetime.time(17, 30)
    """
    if value is None:
        return None

    # Normalize tz input
    if isinstance(tz, str):
        tz = pytz.timezone(tz)

    # Case 1: datetime
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone=pytz.UTC)
        return timezone.localtime(value, tz)

    # Case 2: time
    elif isinstance(value, time):
        today = date.today()
        dt = datetime.combine(today, value)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone=pytz.UTC)
        local_dt = timezone.localtime(dt, tz)
        return local_dt.time()

    else:
        raise TypeError("Value must be a datetime or time object.")


def collapse_inline_spaces(text: str) -> str:
    # Keep line breaks, but collapse runs of spaces/tabs
    return re.sub(r"[^\S\r\n]+", " ", text)
