from django.db import models
from mechanic_workshop.models.base import MechanicWorkshop, MechanicWorkshopTeamMember
from django.utils import timezone
from core.models import BaseTimestamp
from mechanic_workshop.models.vehicles import CustomerVehicle
from django.core.exceptions import ValidationError
from django.db import transaction
from customers.models import WorkshopCustomer
from mechanic_workshop.models.warehouses import WarehouseItem
from core.utils.base import HEX_COLOR_VALIDATOR


class WorkOrderAssignment(BaseTimestamp):
    work_order = models.ForeignKey(
        "WorkOrder", on_delete=models.CASCADE, related_name="assignments"
    )
    assignee = models.ForeignKey(
        MechanicWorkshopTeamMember,
        on_delete=models.CASCADE,
        related_name="work_order_assignments",
        blank=True,
        null=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    price_per_hour = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(null=True, blank=True, max_length=1024)
    work_done = models.TextField(null=True, blank=True, max_length=1024)

    class Meta:
        verbose_name = "Work Order Assignment"
        verbose_name_plural = "Work Order Assignments"
        indexes = [
            models.Index(fields=["assignee", "started_at"]),
            models.Index(fields=["work_order", "started_at"]),
        ]

    def __str__(self):
        return f"{self.work_order} | {self.assignee}"

    def clean(self):
        """Validate time coherence: started <= ended, if both are set."""
        if self.started_at and self.ended_at and self.ended_at < self.started_at:
            raise ValidationError(
                {"ended_at": "ended_at cannot be earlier than started_at"}
            )

    @property
    def is_active(self) -> bool:
        """True if assignment is currently ongoing."""
        now = timezone.now()
        if self.started_at and self.ended_at:
            return self.started_at <= now <= self.ended_at
        if self.started_at and not self.ended_at:
            return self.started_at <= now
        return False


class WorkOrder(BaseTimestamp):
    class Stage(models.TextChoices):
        CHECKIN = "CHECKIN", "Check In"  # vehicle reception
        DIAGNOSIS = "DIAGNOSIS", "Diagnosis"
        REPAIR = "REPAIR", "Repair"
        QA = "QA", "Quality Assurance"
        READY = "READY", "Ready for pickup"
        DELIVERED = "DELIVERED", "Delivered"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ON_HOLD = "ON_HOLD", "On hold"
        BILLED = "BILLED", "Billed"
        CANCELLED = "CANCELLED", "Cancelled"
        CLOSED = "CLOSED", "Closed"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class View(models.TextChoices):
        FRONT = "FRONT", "Front"
        REAR = "REAR", "Rear"
        LEFT = "LEFT", "Left side"
        RIGHT = "RIGHT", "Right side"

    # General information
    # signature = models.ImageField(upload_to="workorders/signatures")
    customer_vehicle = models.ForeignKey(
        CustomerVehicle, on_delete=models.CASCADE, related_name="work_orders"
    )
    vehicle_presenter = models.ForeignKey(
        WorkshopCustomer,
        on_delete=models.SET_NULL,
        related_name="vehicles_presented_to_workshops",
        blank=True,
        null=True,
    )
    workshop = models.ForeignKey(
        MechanicWorkshop,
        on_delete=models.CASCADE,
        related_name="workorders",
        null=True,
        blank=True,
    )
    attended_by = models.ForeignKey(
        MechanicWorkshopTeamMember,
        on_delete=models.SET_NULL,
        related_name="work_orders_attended",
        blank=True,
        null=True,
    )
    customer_telephone = models.CharField(max_length=30, blank=True)
    # Car information
    description = models.TextField(null=True, blank=True, max_length=1000)
    observations = models.TextField(null=True, blank=True, max_length=1000)
    start_mileage = models.PositiveIntegerField(blank=True, null=True)
    end_mileage = models.PositiveIntegerField(blank=True, null=True)
    fuel_level = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True
    )
    damage = models.JSONField(null=True, blank=True)
    lights = models.JSONField(null=True, blank=True)

    # Workflow Metadata
    stage = models.CharField(
        max_length=16, choices=Stage.choices, default=Stage.CHECKIN, db_index=True
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    priority = models.CharField(
        max_length=16, choices=Priority.choices, default=Priority.NORMAL, db_index=True
    )
    price_per_hour = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default="EUR")  # ISO 4217

    # Timing
    car_entered = models.DateField(default=timezone.now)
    car_left = models.DateField(null=True, blank=True)

    # Insurance company
    insurance_company_info = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        verbose_name = "Work Order"
        verbose_name_plural = "Work Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.workshop} | {self.workshop_number}"

    # Business helpers
    def ensure_sequential_number(self):
        """
        Assign a sequential number unique per workshop if not already set.
        Keep it simple; if you need race-safety at scale, wrap in a DB-level
        transaction and SELECT ... FOR UPDATE on a counter table.
        """
        if self.workshop_number is not None:
            return
        last = (
            WorkOrder.objects.filter(workshop=self.workshop)
            .exclude(number__isnull=True)
            .order_by("-workshop_number")
            .values_list("workshop_number", flat=True)
            .first()
        )
        self.workshop_number = (last or 0) + 1

    def assign_next_number(self):
        """Assign the next available workshop_number to this work order."""
        with transaction.atomic():
            mechanic_workshop: MechanicWorkshop = self.workshop

    # Convenience helpers
    def active_assignments(self):
        """Return active assignment segments (now within [started, ended] or open-ended)."""
        now = timezone.now()
        return self.assignments.filter(
            models.Q(started_at__lte=now)
            & (models.Q(ended_at__isnull=True) | models.Q(ended_at__gte=now))
        ).select_related("assignee")

    def current_assignees(self):
        """Return distinct assignees currently active on this WO."""
        return self.active_assignments().values_list("assignee", flat=False).distinct()

    # NOTE: This is a very expensive query, so you should use it sparingly.
    # qs = (
    #     WorkOrder.objects
    #     .select_related(
    #         "customer_vehicle__main_workshop",  # for .workshop property
    #         "customer_vehicle__customer",       # for .get_customer property
    #     )
    # )
    @property
    def workshop(self):
        return self.customer_vehicle.main_workshop

    @property
    def customer(self):
        return self.customer_vehicle.customer


class WorkOrderDamageSketch(BaseTimestamp):
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name="damage_sketches"
    )
    bg_car_id = models.CharField(max_length=64, null=True, blank=True)
    stroke_color = models.CharField(
        max_length=7, null=True, blank=True, validators=[HEX_COLOR_VALIDATOR]
    )

    # Sketches information
    front_strokes = models.JSONField(null=True, blank=True)
    rear_strokes = models.JSONField(null=True, blank=True)
    left_strokes = models.JSONField(null=True, blank=True)
    right_strokes = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Work Order Damage Sketch"
        verbose_name_plural = "Work Order Damage Sketches"
        ordering = ["-created_at"]


# class CarSketchTemplate(models.Model):
#     brand = models.CharField(max_length=50)
#     model = models.CharField(max_length=50, null=True, blank=True)
#     year_from = models.IntegerField(null=True, blank=True)
#     year_to = models.IntegerField(null=True, blank=True)
#     bg_front = models.FileField(upload_to="sketches/")
#     bg_rear = models.FileField(upload_to="sketches/")
#     bg_left = models.FileField(upload_to="sketches/")
#     bg_right = models.FileField(upload_to="sketches/")


class ReplacementPart(models.Model):
    "Ojo, habria que incluir los items del warehouse aqui"

    workorder = models.ForeignKey(
        WorkOrderAssignment, on_delete=models.CASCADE, related_name="replacement_parts"
    )
    # Relation to the items
    warehouse_item = models.ForeignKey(
        WarehouseItem, on_delete=models.CASCADE, related_name="replacement_parts"
    )
    # General Information
    title = models.CharField(max_length=128, null=True, blank=True)
    description = models.TextField(max_length=1024, null=True, blank=True)
    brand = models.CharField(max_length=64, null=True, blank=True)
    provider = models.CharField(max_length=128, null=True, blank=True)

    # Pricing info
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )  # cost to workshop
    list_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )  # P.V.P.
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )  # dto %
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )  # importe final
    currency = models.CharField(max_length=3, default="EUR")  # ISO 4217


class Discount(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "Percentage"
        FIXED_AMOUNT = "FIXED_AMOUNT", "Fixed Amount"

    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name="discounts"
    )
    # Discount information
    discount_type = models.CharField(
        max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE
    )
    value = models.DecimalField(max_digits=10, decimal_places=2)  # could be 10% or 50€
    reason = models.CharField(
        max_length=255, null=True, blank=True
    )  # e.g. "Loyalty", "Promotional code", "Negotiated deal"

    # Valid dates
    valid_from = models.DateField(default=timezone.now)
    valid_until = models.DateField(null=True, blank=True)
    applies_to_total = models.BooleanField(
        default=True
    )  # True = order-level, False = item-level (future proof)
    note = models.TextField(null=True, blank=True, max_length=512)

    class Meta:
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"
        ordering = ["-valid_from"]

    def __str__(self):
        symbol = "%" if self.discount_type == self.DiscountType.PERCENTAGE else "€"
        return f"{self.work_order} | {self.value}{symbol}"
