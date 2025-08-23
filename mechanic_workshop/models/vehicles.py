from django.db import models
from mechanic_workshop.models.base import MechanicWorkshop, MechanicWorkshopTeamMember
from core.models import BaseTimestamp
from customers.models import WorkshopCustomer


class CustomerVehicle(BaseTimestamp):
    main_workshop = models.ForeignKey(
        MechanicWorkshop, on_delete=models.CASCADE, related_name="customer_vehicles"
    )
    # Customer information
    customer = models.ForeignKey(
        WorkshopCustomer,
        on_delete=models.CASCADE,
        related_name="vehicles_in_workshops",
    )
    # General Information
    brand = models.CharField(max_length=128, null=True, blank=True)
    model = models.CharField(max_length=128, null=True, blank=True)
    lisence_plate = models.CharField(max_length=32, null=True, blank=True)
    vin_number = models.CharField(max_length=64, null=True, blank=True)
    color = models.CharField(max_length=32, null=True, blank=True)
    manufactured_at = models.PositiveIntegerField(null=True, blank=True)  # Car year

    # This simple or
    motor_number = models.CharField(
        max_length=32, null=True, blank=True
    )  # e.g. 2.9D 4EA 88
    # This advanced info
    motor_brand = models.CharField(max_length=32, null=True, blank=True)
    cilinders = models.PositiveIntegerField(null=True, blank=True)
    cylinder_size = models.CharField(max_length=16, null=True, blank=True)
    engine_power = models.PositiveIntegerField(null=True, blank=True)  # cm^2
    fuel_type = models.CharField(max_length=16, null=True, blank=True)

    class Meta:
        verbose_name = "Customer Vehicle"
        verbose_name_plural = "Customer Vehicles"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.brand} {self.model} ({self.customer.name or self.customer.first_name})"
