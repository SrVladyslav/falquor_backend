from django.db import models
from mechanic_workshop.models.base import MechanicWorkshop
from django.utils import timezone
from core.models import BaseTimestamp
from mechanic_workshop.models.vehicles import CustomerVehicle
from django.core.exceptions import ValidationError
from django.db import transaction
from mechanic_workshop.models.warehouses import WarehouseItem
from core.utils.base import HEX_COLOR_VALIDATOR
from users.models import WorkspaceMember


class WorkOrderAssignment(BaseTimestamp):
    work_order = models.ForeignKey(
        "WorkOrder", on_delete=models.CASCADE, related_name="assignments"
    )
    assignee = models.ForeignKey(
        WorkspaceMember,
        on_delete=models.CASCADE,
        related_name="workorder_assignments",
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
    # Checksum is used to hash all the data while signing the document by the customer
    checksum = models.CharField(max_length=64, null=True, blank=True)
    customer_vehicle = models.ForeignKey(
        CustomerVehicle,
        on_delete=models.CASCADE,
        related_name="work_orders",
        db_index=True,
    )
    vehicle_presenter = models.ForeignKey(
        WorkspaceMember,
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
        db_index=True,
    )
    attended_by = models.ForeignKey(
        WorkspaceMember,
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
    start_fuel_level = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True
    )
    end_fuel_level = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True
    )
    vehicle_sketch_model = models.CharField(max_length=64, null=True, blank=True)
    damage = models.JSONField(null=True, blank=True)
    lights = models.JSONField(null=True, blank=True)

    # Legal information
    allow_repair_vehicle = models.BooleanField(default=False)
    client_wants_replacements_back = models.BooleanField(default=False)

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

    # Workorder stuff
    workshop_number = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Work Order"
        verbose_name_plural = "Work Orders"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workshop", "workshop_number"],
                name="uniq_workshop_workshop_number",
            )
        ]

    def __str__(self):
        return f"{self.workshop} | {self.workshop_number}"

    # Business helpers
    def _ensure_workshop(self) -> None:
        """
        Ensure the workshop FK is set.
        If not explicitly provided, fallback to the vehicle main workshop.
        """
        if self.workshop_id is None and self.customer_vehicle_id is not None:
            self.workshop = self.customer_vehicle.main_workshop

    def ensure_sequential_number(self):
        """
        Assign a sequential number unique per workshop if not already set.
        Keep it simple; if you need race-safety at scale, wrap in a DB-level
        transaction and SELECT ... FOR UPDATE on a counter table.
        """
        if self.workshop_number is not None:
            return

        # Make sure workshop FK is populated
        self._ensure_workshop()
        if self.workshop_id is None:
            # If this happens you have a workflow bug: you cannot number without workshop.
            raise ValueError(
                "WorkOrder.ensure_sequential_number: workshop is required."
            )

        with transaction.atomic():
            # Lock existing rows for this workshop while we compute the next number.
            last_number = (
                WorkOrder.objects.select_for_update()
                .filter(workshop=self.workshop)
                .aggregate(max_no=models.Max("workshop_number"))
                .get("max_no")
                or 0
            )
            self.workshop_number = last_number + 1

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

    def save(self, *args, **kwargs) -> None:
        """
        Override save to automatically assign workshop_number on creation.

        If you ever need to manually override workshop_number,
        just set it before calling save(), and this logic will not touch it.
        """
        is_new = self.pk is None

        # Always ensure workshop is consistent
        self._ensure_workshop()

        if is_new:
            self.ensure_sequential_number()

        super().save(*args, **kwargs)

    # NOTE: This is a very expensive query, so you should use it sparingly.
    # qs = (
    #     WorkOrder.objects
    #     .select_related(
    #         "customer_vehicle__main_workshop",  # for .workshop property
    #         "customer_vehicle__customer",       # for .get_customer property
    #     )
    # )
    @property
    def main_workshop(self) -> MechanicWorkshop:
        """
        Convenience property to access the main workshop from the vehicle.
        Does NOT replace the workshop FK.
        """
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
