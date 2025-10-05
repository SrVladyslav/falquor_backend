from django.db import models
from core.models import (
    BusinessOrganization,
    BaseTimestamp,
    # WeekWorkingHours,
    Language,
    Tag,
)
from core.ctmodels import WeekWorkingHours
from users.models import Account
from django.contrib.contenttypes.fields import GenericRelation


class MechanicWorkshop(BusinessOrganization):
    # Specific Services info
    has_towing_service = models.BooleanField(default=False)
    has_car_service = models.BooleanField(default=False)
    languages_spoken = models.ManyToManyField(Language, blank=True)

    # Reverse generic relation (convenience)
    week_hours = GenericRelation(
        WeekWorkingHours,
        content_type_field="content_type",
        object_id_field="object_id",
        related_query_name="workshop",
    )

    # Optional: coordinates if you dispatch mobile techs
    latitude = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )

    @property
    def users(self):
        return Account.objects.filter(
            mechanic_workshops__workshop=self
        ).distinct()  # .prefetch_related("mechanic_workshops")

    @property
    def get_specializations(self):
        return self.workshop_specializations.all()

    def __str__(self):
        return f"{self.business_name} | {self.tax_id} | {self.email} | {self.country} - {self.city} - {self.address}"

    class Meta:
        verbose_name = "Mechanic Workshop"
        verbose_name_plural = "Mechanic Workshops"


class MechanicWorkshopTeamMember(BaseTimestamp):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        TECHNICHIAN = "TECHNICIAN", "Technician"
        VIEWER = "VIEWER", "Viewer"

    workshop = models.ForeignKey(
        MechanicWorkshop, on_delete=models.CASCADE, related_name="members"
    )
    user_account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="mechanic_workshops"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name="invited_to_mechanic_workshops",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Mechanic Workshop Team Member"
        verbose_name_plural = "Mechanic Workshop Team Members"


class MechanicWorkshopSpecializationTag(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="tag_workshops")
    workshop = models.ForeignKey(
        MechanicWorkshop,
        on_delete=models.CASCADE,
        related_name="specialization_tags",
        blank=True,
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tag", "workshop"],
                name="unique_tag_workshop",
            )
        ]
        ordering = ["tag", "workshop"]


class MechanicWorkshopSpecialization(models.Model):
    workshop = models.ForeignKey(
        MechanicWorkshop,
        on_delete=models.CASCADE,
        related_name="workshop_specializations",
        blank=True,
        null=True,
    )
    specialization = models.ForeignKey(
        "Specialization",
        on_delete=models.CASCADE,
        related_name="workshop_links",
        blank=True,
        null=True,
    )

    # Personalization per link
    is_licensed = models.BooleanField(default=False)
    license_number = models.CharField(max_length=64, blank=True, default="")
    notes = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        verbose_name = "Mechanic Workshop Specialization Link"
        verbose_name_plural = "Mechanic Workshop Specialization Links"
        ordering = ["workshop", "specialization"]

    def __str__(self):
        return f"{self.workshop} | {self.specialization} ({'Licensed' if self.is_licensed else 'Unlicensed'})"


class Specialization(models.Model):
    name = models.CharField(max_length=120, unique=True)
