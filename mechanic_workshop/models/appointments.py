from django.db import models
from core.models import BaseTimestamp
from customers.models import WorkshopCustomer
from mechanic_workshop.models.base import MechanicWorkshop, MechanicWorkshopTeamMember
from mechanic_workshop.models.vehicles import CustomerVehicle
from django.core.exceptions import ValidationError


class AppointmentType(models.TextChoices):
    GENERAL = "GENERAL", "General"
    MAINTENANCE = "MAINTENANCE", "Maintenance / Service"
    DIAGNOSTIC = "DIAGNOSTIC", "Diagnostic"
    TIRE = "TIRE", "Tires / Wheels"
    BODY_PAINT = "BODY_PAINT", "Body & Paint"
    ELECTRICAL = "ELECTRICAL", "Electrical / Electronics"
    AC = "AC", "A/C & Climate"
    BRAKES = "BRAKES", "Brakes"
    INSPECTION = "INSPECTION", "Inspection / Pre-ITV"
    WARRANTY = "WARRANTY", "Warranty"
    QUOTE = "QUOTE", "Quote / Estimate"
    DELIVERY_PICKUP = "DELIVERY_PICKUP", "Delivery / Pickup"
    EMERGENCY = "EMERGENCY", "Emergency"


class AppointmentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SCHEDULED = "SCHEDULED", "Scheduled"
    CONFIRMED = "CONFIRMED", "Confirmed"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    NO_SHOW = "NO_SHOW", "No-show"
    CANCELED = "CANCELED", "Canceled"
    RESCHEDULED = "RESCHEDULED", "Rescheduled"


class Appointment(BaseTimestamp):
    workshop_customer = models.ForeignKey(
        WorkshopCustomer,
        on_delete=models.CASCADE,
        related_name="appointments",
        null=True,
        blank=True,
    )
    workshop = models.ForeignKey(  # denormalized for fast filtering/joins
        MechanicWorkshop,
        on_delete=models.CASCADE,
        related_name="appointments",
        null=True,
        blank=True,
    )
    customer_vehicle = models.ForeignKey(
        CustomerVehicle,
        on_delete=models.CASCADE,
        related_name="appointments",
        null=True,
        blank=True,
    )
    workshop_team_member = models.ForeignKey(
        MechanicWorkshopTeamMember,
        on_delete=models.CASCADE,
        related_name="appointments",
        null=True,
        blank=True,
    )
    # Core Information
    appointment_start = models.DateTimeField(null=False, blank=False)
    appointment_end = models.DateTimeField(null=True, blank=True)
    appointment_type = models.CharField(
        max_length=24, choices=AppointmentType.choices, default=AppointmentType.GENERAL
    )
    status = models.CharField(
        max_length=16,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.SCHEDULED,
    )

    # General Information
    title = models.CharField(max_length=128, blank=True, default="")
    description = models.TextField(blank=True, default="", max_length=1024)

    # Location (on-site vs off-site)
    onsite = models.BooleanField(default=True)
    location_text = models.CharField(  # free text address/notes
        max_length=240, blank=True, default=""
    )

    # Optional: coordinates if you dispatch mobile techs
    latitude = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )

    # Confirmation and reminders
    reminders_status = models.IntegerField(
        default=-1
    )  # Send message x days before, or -1 if deactivated

    # Cancellation / Reshchedule
    cancellation_reason = models.CharField(
        max_length=256, blank=True, default=""
    )  # e.g. "Customer cancelled appointment"
    rescheduled_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reschedules",
    )

    class Meta:
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        ordering = ["appointment_start"]

        constraints = [
            # enforce start < end at DB level if both present
            models.CheckConstraint(
                check=(
                    models.Q(appointment_start__isnull=True)
                    | models.Q(appointment_end__isnull=True)
                    | models.Q(appointment_end__gt=models.F("appointment_start"))
                ),
                name="ck_appt_start_before_end",
            ),
        ]

    def __str__(self):
        who = self.workshop_customer or self.customer_vehicle or "Unassigned"
        when = self.appointment_start.isoformat() if self.appointment_start else "TBD"
        return f"{self.workshop} | {self.customer_vehicle} | {self.appointment_start} @ {when} ({who})"

    @property
    def is_confirmed(self):
        return self.status == AppointmentStatus.CONFIRMED

    def clean(self):
        if self.appointment_end and self.appointment_end <= self.appointment_start:
            raise ValidationError({"end": "End time must be greater than start time."})
