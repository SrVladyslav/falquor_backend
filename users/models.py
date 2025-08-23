from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
import secrets
from django.conf import settings
from django.utils import timezone
from core.utils.base import obfuscate_email
from core.models import BaseUUID, MarketingSettings, BaseTimestamp


class UserToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_tokens"
    )

    access_token = models.TextField(blank=True, unique=True)
    refresh_token = models.TextField(blank=True, unique=True)
    device = models.CharField(
        max_length=64, blank=True
    )  # e.g: "PC", "Mobile", "Tablet"
    user_agent = models.CharField(max_length=256, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    refresh_expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["access_token"]),
            models.Index(fields=["refresh_token"]),
        ]

    def is_valid(self):
        return not self.revoked and self.expires_at > timezone.now()

    def is_expired(self):
        return timezone.now() >= self.expires_at or self.revoked

    def __str__(self):
        return f"{self.user.uuid} | {self.user.email} | Rewoked: {'YES' if self.revoked else 'NO'} | {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class EmailUserManager(BaseUserManager):
    def create_user(self, email, username=None):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username)
        user.set_unusable_password()  # ← normal user can not use password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, username=None):
        if not email:
            raise ValueError("Superusers must have an email address")
        if not password:
            raise ValueError("Superusers must have a password")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username or email.split("@")[0])
        user.set_password(password)
        user.is_staff = True
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


# class UserType(models.TextChoices):
#     CUSTOMER = "CUSTOMER", "Customer"
#     BUSINESS_OWNER = "BUSINESS_OWNER", "Business Owner"
#     ADMIN = "ADMIN", "Admin"


class Account(
    AbstractBaseUser, PermissionsMixin, BaseTimestamp, BaseUUID, MarketingSettings
):
    # Authentication
    email = models.EmailField(verbose_name="email", max_length=70, unique=True)
    otp_code = models.CharField(max_length=6, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_tries = models.IntegerField(
        default=0
    )  # Number of tries to set an OTP before block
    blocked_until = models.DateTimeField(
        null=True, blank=True
    )  # Blocked in case of too many failed otp attempts
    jwt_secret = models.CharField(max_length=64, default=secrets.token_hex)

    # Secutiry
    last_ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_user_agent = models.CharField(max_length=256, blank=True)
    last_login = models.DateTimeField(verbose_name="last_login", auto_now=True)
    is_suspected_bot = models.BooleanField(default=False)
    account_suspended = models.BooleanField(default=False)

    # Permissions
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # Generic Info
    username = models.CharField(max_length=30, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    birthday = models.DateField(null=True, blank=True)
    preferred_language = models.CharField(max_length=10, default="es")  # ISO code
    hide_email = models.BooleanField(default=True)
    date_joined = models.DateTimeField(verbose_name="date_joined", auto_now_add=True)

    objects = EmailUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return obfuscate_email(email=self.email) if self.hide_email else self.email

    def has_perm(self, perm, obj=None):
        return self.is_superuser or self.is_admin

    def has_module_perms(self, app_label):
        return self.is_superuser

    class Meta:
        verbose_name = "Email User"
        permissions = [
            ("can_invite_users", "Can invite users"),  # Let's copy forocoches schema
        ]
