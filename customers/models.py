from django.db import models
from core.models import BaseTimestamp, BaseUUID, MarketingSettings
from mechanic_workshop.models.base import MechanicWorkshop
from users.models import Account
from django.db.models import Q, CheckConstraint


class WorkshopCustomer(BaseTimestamp, BaseUUID, MarketingSettings):
    class Type(models.TextChoices):
        PERSON = "PERSON", "Person"
        COMPANY = "COMPANY", "Company"

    class DocumentType(models.TextChoices):
        DNI = "DNI"
        NIE = "NIE"
        NIF = "NIF"
        PASSPORT = "PASSPORT"
        OTHER = "OTHER"

    mechanic_workshop = models.ForeignKey(
        MechanicWorkshop, on_delete=models.CASCADE, null=True, blank=True
    )
    customer_type = models.CharField(
        max_length=10, choices=Type.choices, default=Type.PERSON
    )
    user_account = models.ForeignKey(
        Account, on_delete=models.CASCADE, null=True, blank=True
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
        choices=DocumentType, max_length=32
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

    # More custom info
    account_active = models.BooleanField(
        default=True
    )  # Is Active, should be checked with the membership

    # Platform payment info
    account_credits = models.IntegerField(default=0)
    # Extra feature
    is_defaulter = models.BooleanField(default=False)  # Moroso

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                check=Q(name__isnull=False, name__gt=""),
                name="name_or_firstname_required",
            )
        ]

    def __str__(self):
        return f"{self.name or self.first_name} ({self.email} | {self.phone})"

    @property
    def is_business(self):
        return self.document_type == self.DocumentType.NIF

    @property
    def vehicles_in_property(self):
        return 3  # todo

    @property
    def has_platform_account(self):
        return self.user_account is not None


class CustomerExtraData(models.Model):
    customer = models.ForeignKey(
        WorkshopCustomer, on_delete=models.CASCADE, related_name="extra_data"
    )
    version = models.IntegerField(default=1)
    comments = models.TextField(null=True, blank=True, max_length=1000)
