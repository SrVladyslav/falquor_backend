from django.db import models, transaction, router, IntegrityError
import uuid
from django.utils.text import slugify
from core.utils.base import current_time, generate_nanoid
from django.core.exceptions import ValidationError

# from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
# from django.contrib.contenttypes.models import ContentType
from core.utils.base import HEX_COLOR_VALIDATOR
from typing import Optional
from django.core.validators import RegexValidator
import pycountry

LANGUAGE_DICT = {
    lang.alpha_2: lang.name for lang in pycountry.languages if hasattr(lang, "alpha_2")
}
LANGUAGE_CHOICES = list(
    LANGUAGE_DICT.items()
)  # e.g. [("en", "English"), ("es", "Spanish")...]


class Language(models.Model):
    lang_id = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        default="es",
        db_index=True,
        unique=True,
    )
    lang_name = models.CharField(max_length=100, editable=False)

    def save(self, *args, **kwargs):
        """Automatically fill lang_name base on lang_id using LANGUAGE_DICT."""
        if self.lang_id in LANGUAGE_DICT:
            self.lang_name = LANGUAGE_DICT[self.lang_id]
        else:
            self.lang_name = self.lang_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.lang_name} ({self.lang_id})"


class BaseTimestamp(models.Model):
    """
    Base class which provides a TimestampField
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseUUID(models.Model):
    """Abstract class which sets the primary key as UUID."""

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseNanoID(models.Model):
    """Abstract class which sets the primary key as NanoID."""

    wid = models.CharField(
        max_length=12, primary_key=True, editable=False, default=generate_nanoid
    )

    class Meta:
        abstract = True

    @classmethod
    def _new_wid(cls) -> str:
        """Generate a new NanoID candidate."""
        return generate_nanoid()

    def save(self, *args, **kwargs):
        """
        Save with collision- and race-safety:
        - If wid missing, generate one.
        - Retry on IntegrityError up to `max_attempts`.
        """
        max_attempts: int = kwargs.pop("max_attempts", 10)
        using: Optional[str] = kwargs.get("using") or router.db_for_write(
            self.__class__
        )

        # Ensure we have a candidate before first attempt
        if not self.wid:
            self.wid = self._new_wid()

        # Try to persist; if a race triggers IntegrityError on PK, retry with a new wid
        for attempt in range(1, max_attempts + 1):
            try:
                with transaction.atomic(using=using):
                    return super().save(*args, **kwargs)
            except IntegrityError as exc:
                # If the PK collided (extremely rare), generate a new candidate and retry
                if attempt < max_attempts:
                    self.wid = self._new_wid()
                    continue
                raise RuntimeError(
                    f"Failed to persist unique wid after {max_attempts} attempts"
                ) from exc


class MarketingSettings(models.Model):
    allow_marketing_emails = models.BooleanField(default=False)
    allow_ads_personalization = models.BooleanField(default=True)

    class Meta:
        abstract = True


class BusinessOrganization(BaseUUID, BaseTimestamp):
    # Multi Business
    parent_organization = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True
    )

    # Fraud control
    # max_parallel_active_devices = models.PositiveIntegerField(default=1)
    # device_update_reload_time

    # Base information
    business_name = models.CharField(max_length=100, null=False)
    tax_id = models.CharField(max_length=50, blank=True)  # CIF/NIF
    fax = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(max_length=100)
    website = models.URLField(blank=True)

    # Location
    address = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=15, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Time Zone
    time_zone = models.CharField(max_length=100, blank=True, default="Europe/Madrid")

    # Activity
    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.business_name} | {self.tax_id}"

    class Meta:
        abstract = True
        verbose_name = "Business Organization"
        verbose_name_plural = "Business Organizations"


class BaseNotification(BaseTimestamp):
    class Type(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        SMS = "SMS", "SMS"
        PUSH = "PUSH", "Push"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    message = models.TextField(null=True, blank=True, max_length=1000)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.EMAIL)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    sender = models.EmailField(max_length=100)
    recipient = models.EmailField(max_length=100)

    def __str__(self):
        return f"{self.message} | {self.type} | {self.status}"

    class Meta:
        abstract = True


class BaseTag(models.Model):
    """
    Base for customizable labels/tags per workshop:
    - name: display text
    - slug: stable key for code/filters ("ready", "diagnosis", etc.)
    - text_color / bg_color: theme for pill/badge
    - order: sorting in UI
    - is_default: created by system as default set (can be edited or hidden)
    - is_active: soft toggle without deleting usages
    """

    name = models.CharField(max_length=32, null=False, blank=False)
    slug = models.CharField(max_length=32, null=False, blank=False)
    description = models.CharField(max_length=128, null=True, blank=True)
    text_color = models.CharField(
        max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#111827"  # gray-900
    )
    bg_color = models.CharField(
        max_length=7, validators=[HEX_COLOR_VALIDATOR], default="#E5E7EB"  # gray-200
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["name"]
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def save(self, *args, **kwargs):
        # Auto-generate slug from name if not provided
        if not self.slug:
            self.slug = slugify(self.name)[:32]
        super().save(*args, **kwargs)


# class TimeSlot(models.Model):
#     start = models.TimeField(default=current_time)
#     end = models.TimeField()

#     class Meta:
#         verbose_name = "Time Slot"
#         verbose_name_plural = "Time Slots"
#         ordering = ["start"]

#     def __str__(self):
#         return f"{self.start} - {self.end}"

#     def clean(self):
#         if self.end <= self.start:
#             raise ValidationError({"end": "End time must be greater than start time."})


# class Day(models.TextChoices):
#     MONDAY = "MONDAY", "Monday"
#     TUESDAY = "TUESDAY", "Tuesday"
#     WEDNESDAY = "WEDNESDAY", "Wednesday"
#     THURSDAY = "THURSDAY", "Thursday"
#     FRIDAY = "FRIDAY", "Friday"
#     SATURDAY = "SATURDAY", "Saturday"
#     SUNDAY = "SUNDAY", "Sunday"


# class WeekWorkingHours(models.Model):
#     # Hot deactivation of working hours
#     deactivate_working_hours = models.BooleanField(default=False)

#     # Working hours
#     time_slot = models.ForeignKey(
#         TimeSlot, on_delete=models.CASCADE, related_name="working_hours"
#     )
#     day = models.CharField(max_length=10, choices=Day.choices, default=Day.MONDAY)
#     notes = models.CharField(max_length=256, blank=True, default="")

#     # --- Generic owner (the entity this row belongs to) ---
#     content_type = models.ForeignKey(
#         ContentType, on_delete=models.CASCADE, db_index=True
#     )
#     object_id = models.PositiveBigIntegerField(db_index=True)
#     company = GenericForeignKey("content_type", "object_id")

#     class Meta:
#         verbose_name = "Week Working Hours"
#         verbose_name_plural = "Week Working Hours"
#         ordering = ["time_slot"]

#     def __str__(self):
#         state = "OPEN" if not self.deactivate_working_hours else "OFF"
#         return f"{self.content_type.model}:{self.object_id} | {self.day} {self.time_slot} {state}"
