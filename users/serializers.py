# users/serializers.py
import re
import unicodedata
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.validators import RegexValidator
from rest_framework.validators import UniqueValidator
from users.models import Account
from typing import Any

User = get_user_model()

ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]")
ALLOWED_USERNAME_RE = r"^[A-Za-z0-9._-]+$"

RESERVED_USERNAMES = {
    "admin",
    "root",
    "system",
    "support",
    "security",
    "null",
    "none",
    "undefined",
    "api",
    "staff",
    "moderator",
    "owner",
    "me",
    "you",
}


class UsernameUpdateSerializer(serializers.Serializer):
    """
    Safe username update: normalize, strip zero-width, enforce allow-list,
    check reserved and case-insensitive uniqueness.
    """

    username = serializers.CharField(
        min_length=2,
        max_length=32,
        trim_whitespace=True,
        validators=[
            RegexValidator(
                regex=ALLOWED_USERNAME_RE,
                message="Only letters, numbers, dot, dash or underscore.",
                code="invalid_chars",
            ),
        ],
    )

    def _sanitize(self, value: str) -> str:
        # Unicode normalize to NFKC (mitigates lookalike/homoglyph tricks)
        v = unicodedata.normalize("NFKC", value)
        # Remove zero-width (invisible) characters
        v = ZERO_WIDTH_RE.sub("", v)
        # Disallow any whitespace entirely (just in case)
        v = "".join(ch for ch in v if not ch.isspace())
        return v

    def validate_username(self, value: str) -> str:
        v = self._sanitize(value)

        # Re-run allow-list after sanitation to be strict
        if not re.fullmatch(ALLOWED_USERNAME_RE, v or ""):
            raise serializers.ValidationError(
                "Only letters, numbers, dot, dash or underscore."
            )

        # Reserved
        if v.lower() in RESERVED_USERNAMES:
            raise serializers.ValidationError("This username is not allowed.")

        # Case-insensitive uniqueness (exclude current user)
        request = self.context.get("request")
        qs = User.objects.filter(username__iexact=v)
        if request and request.user and request.user.is_authenticated:
            qs = qs.exclude(pk=request.user.pk)
        if qs.exists():
            raise serializers.ValidationError("This username is already taken.")

        return v


class PreferencesUpdateSerializer(serializers.Serializer):
    """
    Validates and applies account preferences updates:
    - Input keys: {"language": "en", "icon_style": "DEFAULT"}
    - Writes to model fields: preferred_locale, icon_style
    - Either field is optional, but at least one must be provided.
    """

    # Accept incoming form keys (language, icon_style)
    language = serializers.ChoiceField(
        choices=[c for c, _ in User.AllowedLocales.choices],
        required=False,
        help_text="Two-letter locale code (e.g., 'en', 'es', 'uk', 'ru').",
    )
    icon_style = serializers.ChoiceField(
        choices=[c for c, _ in User.IconStyle.choices],
        required=False,
        help_text="Icon style identifier ('DEFAULT' or 'EMOJI').",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Ensure at least one field is present
        if not attrs:
            raise serializers.ValidationError("At least one field must be provided.")

        # Normalize icon_style to uppercase to be resilient to input casing
        if "icon_style" in attrs and isinstance(attrs["icon_style"], str):
            attrs["icon_style"] = attrs["icon_style"].upper()

        return attrs

    def update(self, instance: Account, validated_data: dict[str, Any]) -> Account:
        """
        Apply changes to the given Account instance and persist selective fields.
        - Maps 'language' -> instance.preferred_locale
        - Maps 'icon_style' -> instance.icon_style
        """
        update_fields = []

        if "language" in validated_data:
            instance.preferred_locale = validated_data["language"]
            update_fields.append("preferred_locale")

        if "icon_style" in validated_data:
            instance.icon_style = validated_data["icon_style"]
            update_fields.append("icon_style")

        if update_fields:
            instance.save(update_fields=update_fields)

        return instance

    def create(self, validated_data: dict[str, Any]):
        raise NotImplementedError


class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["username", "email", "uuid", "is_active", "first_name", "last_name"]
        read_only_fields = fields
