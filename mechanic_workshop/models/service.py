from django.db import models
from core.models import BaseTimestamp
from mechanic_workshop.models.base import MechanicWorkshop, MechanicWorkshopTeamMember
from customers.models import WorkshopCustomer
from django.utils import timezone


class LoanerCar(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        RESERVED = "RESERVED", "Reserved"
        IN_USE = "IN_USE", "In Use"
        MAINTENANCE = "MAINTENANCE", "Under Maintenance"
        INACTIVE = "INACTIVE", "Inactive"

    # Identification
    license_plate = models.CharField(max_length=20)
    vin_number = models.CharField(max_length=50, null=True, blank=True)
    mechanic_workshop = models.ForeignKey(
        MechanicWorkshop, on_delete=models.CASCADE, related_name="loaner_cars"
    )
    # Status
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE
    )
    # Car general information
    car_model = models.CharField(max_length=100, null=True, blank=True)
    car_brand = models.CharField(max_length=100, null=True, blank=True)
    car_year = models.IntegerField(null=True, blank=True)
    mileage = models.PositiveIntegerField(
        default=0
    )  # In km, mileage of the car during its usage in the workshop
    # Features
    fuel_type = models.CharField(
        max_length=30, null=True, blank=True
    )  # Petrol, Diesel, EV, Hybrid
    transmission = models.CharField(
        max_length=20, null=True, blank=True
    )  # Manual, Automatic
    color = models.CharField(
        max_length=20, null=True, blank=True
    )  # Black, White, Red, Green, Blue, Yellow, Purple, Gray, Silver, Gold, etc.
    has_sunroof = models.BooleanField(blank=True)
    has_air_conditioning = models.BooleanField(default=True)
    has_gps = models.BooleanField(default=False)
    has_seat_heating = models.BooleanField(blank=True)

    class Meta:
        verbose_name = "Loaner Car"
        verbose_name_plural = "Loaner Cars"

    def __str__(self):
        return f"{self.car_brand} {self.car_model} ({self.license_plate})"


class LoanerCarHistory(BaseTimestamp):
    used_by = models.ForeignKey(
        WorkshopCustomer, on_delete=models.CASCADE, related_name="loaner_car_history"
    )
    attended_by = models.ForeignKey(
        MechanicWorkshopTeamMember,
        on_delete=models.CASCADE,
        related_name="team_member_attended",
        blank=True,
    )
    loaner_car = models.ForeignKey(
        LoanerCar, on_delete=models.CASCADE, related_name="history"
    )
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    mileage_start = models.PositiveIntegerField(null=True, blank=True)
    mileage_end = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    @property
    def mileage(self):
        if self.mileage_start is None or self.mileage_end is None:
            return -1
        return self.mileage_end - self.mileage_start

    class Meta:
        verbose_name = "Loaner Car History"
        verbose_name_plural = "Loaner Car Histories"

    def __str__(self):
        return (
            f"{self.loaner_car} → {self.used_by} ({self.start_date} - {self.end_date})"
        )
