from django.db import models
from mechanic_workshop.models.base import MechanicWorkshop
from core.models import BaseTimestamp
from users.models import WorkspaceMember


class CustomerVehicle(BaseTimestamp):
    main_workshop = models.ForeignKey(
        MechanicWorkshop, on_delete=models.CASCADE, related_name="customer_vehicles"
    )
    # Customer information
    # TODO: Shoul we add a table of presenter, so many different people can provide a car?
    owner = models.ForeignKey(
        WorkspaceMember,
        on_delete=models.CASCADE,
        related_name="owned_vehicles",
        null=True,
        blank=True,
    )
    # Vehicle brought by to the workshop
    authorized_people = models.ManyToManyField(
        WorkspaceMember, related_name="authorized_vehicles", blank=True
    )
    # General Information
    brand = models.CharField(max_length=128, null=True, blank=True)
    model = models.CharField(max_length=128, null=True, blank=True)
    license_plate = models.CharField(max_length=32, null=True, blank=True)
    vin_number = models.CharField(max_length=64, null=True, blank=True)
    color = models.CharField(max_length=32, null=True, blank=True)
    manufactured_at = models.PositiveIntegerField(null=True, blank=True)  # Car year

    # This simple or
    motor_number = models.CharField(
        max_length=32, null=True, blank=True
    )  # e.g. 2.9D 4EA 88
    # This advanced info
    motor_brand = models.CharField(max_length=32, null=True, blank=True)
    motor_type = models.CharField(max_length=128, null=True, blank=True)
    cylinders = models.PositiveIntegerField(null=True, blank=True)
    cylinder_size = models.CharField(max_length=16, null=True, blank=True)
    engine_power = models.PositiveIntegerField(null=True, blank=True)  # cm^2
    fuel_type = models.CharField(max_length=16, null=True, blank=True)

    class Meta:
        verbose_name = "Customer Vehicle"
        verbose_name_plural = "Customer Vehicles"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["main_workshop", "vin_number", "license_plate"],
                name="uq_vehicle_workshop_vin_plate",
            )
        ]

    def __str__(self):
        return f"{self.brand} {self.model} ({self.license_plate} - {self.main_workshop.business_name})"
