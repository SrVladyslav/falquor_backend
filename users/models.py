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
from core.models import BaseUUID, MarketingSettings, BaseTimestamp, BaseNanoID
from workspace_modules.models.base import Workspace
from django.db.models.functions import Lower
from django.db.models import Q, CheckConstraint


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
    class AllowedLocales(models.TextChoices):
        EN = "en", "English"
        ES = "es", "Spanish"
        UK = "uk", "Ukrainian"
        RU = "ru", "Russian"

    class IconStyle(models.TextChoices):
        DEFAULT = "DEFAULT", "DEFAULT"
        EMOJI = "EMOJI", "EMOJI"

    class AccountType(models.TextChoices):
        PERSONAL = "PERSONAL", "Personal"
        BUSINESS = "BUSINESS", "Business"

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

    # Security
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
    hide_email = models.BooleanField(default=True)
    date_joined = models.DateTimeField(verbose_name="date_joined", auto_now_add=True)

    # Basic Metadata info
    # Account type means that we inccur in some extra costs or not, but also blocks some parts.
    account_type = models.CharField(
        max_length=32, choices=AccountType.choices, default=AccountType.PERSONAL
    )
    preferred_locale = models.CharField(
        choices=AllowedLocales.choices, max_length=3, default=AllowedLocales.EN
    )
    icon_style = models.CharField(
        max_length=32, choices=IconStyle.choices, default=IconStyle.DEFAULT
    )
    selected_workspace = models.ForeignKey(
        Workspace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounts",
    )

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
        verbose_name = "Account"
        permissions = [
            ("can_invite_users", "Can invite users"),  # Let's copy forocoches schema
        ]
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="uniq_account_username_ci",
            )
        ]


class WorkspaceMember(BaseUUID, BaseTimestamp):
    """Official relation between a Workspace and an Account.

    Can represent a Customer, a Team Member or just a some fucking business client
    """

    class WorkspaceRole(models.TextChoices):
        # ADMINS
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"

        # TEAM MEMBERS
        MEMBER = "MEMBER", "Member"
        GUEST = "GUEST", "Guest"
        MANAGER = "MANAGER", "Manager"
        TECHNICHIAN = "TECHNICIAN", "Technician"

        # Just a little CUSTOMERs without any roles
        CUSTOMER = "CUSTOMER", "Customer"
        INVITED = "INVITED", "Invited"
        ON_HOLD = "ON_HOLD", "On Hold"
        VIEWER = "VIEWER", "Viewer"

    class IconStyle(models.TextChoices):
        DEFAULT = "DEFAULT", "Default"
        EMOJI = "EMOJI", "Emoji"
        COLORIZED = "COLORIZED", "Colorized"

    class DocumentType(models.TextChoices):
        PASSPORT = "PASSPORT"
        OTHER = "OTHER"
        # Spanish
        DNI = "DNI"
        NIE = "NIE"
        NIF = "NIF"
        # United Arab Emirates
        TRN = "TRN"
        EID = "EID"
        TRADE_LICENSE = "TradeLicense"
        # Andorra
        NRT = "NRT"
        # Ukraine
        RNOKPP = "RNOKPP"
        EDRPOU = "EDRPOU"
        # Russia
        INN = "INN"
        SNILS = "SNILS"

    class Type(models.TextChoices):
        PERSON = "PERSON", "Person"
        COMPANY = "COMPANY", "Company"

    # General information
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="members",
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="workspace_members"
    )
    customer_type = models.CharField(
        max_length=10, choices=Type.choices, default=Type.PERSON
    )
    invited_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name="invited_members_to_ws",
        null=True,
        blank=True,
    )
    role = models.CharField(
        max_length=32, choices=WorkspaceRole.choices, default=WorkspaceRole.ON_HOLD
    )
    can_manage_billing = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    user_preferences = models.JSONField(null=True, blank=True)
    icon_style = models.CharField(
        max_length=32, choices=IconStyle.choices, default=IconStyle.DEFAULT
    )

    # Base information
    name = models.CharField(max_length=100, blank=True, null=True)
    surname = models.CharField(max_length=100, blank=True)
    alias = models.CharField(max_length=100, blank=True)
    email = models.EmailField(max_length=100, blank=True)
    phone = models.CharField(max_length=100, blank=True)
    phone_2 = models.CharField(max_length=100, blank=True)
    fax = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    time_zone = models.CharField(max_length=100, blank=True, default="Europe/Madrid")

    # Identification number
    tax_id = models.CharField(max_length=50)  # DNI, NIF, etc.
    document_type = models.CharField(
        choices=DocumentType.choices, max_length=32, default=DocumentType.PASSPORT
    )  # DNI, NIF, etc.

    # Location
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=100, blank=True)

    # Payment information
    payment_type = models.CharField(
        max_length=50, blank=True
    )  # Credit card, Paypal, etc.
    iban = models.CharField(max_length=50, blank=True)
    bic = models.CharField(max_length=50, blank=True)
    ccc = models.CharField(max_length=50, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    sepa_date = models.DateField(null=True, blank=True)

    # Spicy information --------------------------------------
    # Platform payment info
    account_credits = models.IntegerField(default=0)
    # Extra feature
    is_defaulter = models.BooleanField(default=False)  # Moroso

    class Meta:
        verbose_name = "Workspace Member"
        verbose_name_plural = "Workspace Members"
        ordering = ["-created_at"]
        unique_together = [("workspace", "account")]
        indexes = [
            models.Index(fields=["workspace", "account", "role", "is_active"]),
        ]
        # constraints = [
        #     CheckConstraint(
        #         check=Q(name__isnull=False, name__gt=""),
        #         name="name_or_firstname_required",
        #     )
        # ]

    def __str__(self):
        return f"({self.email or '-'} | {self.phone or '-'}) | {self.workspace.short_name or self.workspace.wid} | OWNER: {'YES' if self.is_owner else 'NO'} | ADMIN: {'YES' if self.is_admin else 'NO'}"
