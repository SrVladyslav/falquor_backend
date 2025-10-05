from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from core.utils.base import current_time
from django.db import models


class Day(models.TextChoices):
    MONDAY = "MONDAY", "Monday"
    TUESDAY = "TUESDAY", "Tuesday"
    WEDNESDAY = "WEDNESDAY", "Wednesday"
    THURSDAY = "THURSDAY", "Thursday"
    FRIDAY = "FRIDAY", "Friday"
    SATURDAY = "SATURDAY", "Saturday"
    SUNDAY = "SUNDAY", "Sunday"


class TimeSlot(models.Model):
    start = models.TimeField(default=current_time)
    end = models.TimeField()

    class Meta:
        verbose_name = "Time Slot"
        verbose_name_plural = "Time Slots"
        ordering = ["start"]

    def __str__(self):
        return f"{self.start} - {self.end}"

    def clean(self):
        if self.end <= self.start:
            raise ValidationError({"end": "End time must be greater than start time."})


class WeekWorkingHours(models.Model):
    # Hot deactivation of working hours
    deactivate_working_hours = models.BooleanField(default=False)

    # Working hours
    time_slot = models.ForeignKey(
        TimeSlot, on_delete=models.CASCADE, related_name="working_hours"
    )
    day = models.CharField(max_length=10, choices=Day.choices, default=Day.MONDAY)
    notes = models.CharField(max_length=256, blank=True, default="")

    # --- Generic owner (the entity this row belongs to) ---
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, db_index=True
    )
    object_id = models.UUIDField(db_index=True)
    company = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "Week Working Hours"
        verbose_name_plural = "Week Working Hours"
        ordering = ["time_slot"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
        constraints = [
            # Avoid duplicated rows per owner
            models.UniqueConstraint(
                fields=["content_type", "object_id", "day", "time_slot"],
                name="uniq_workinghours_per_owner_day_slot",
            ),
        ]

    def __str__(self):
        state = "OPEN" if not self.deactivate_working_hours else "OFF"
        return f"{self.content_type.model}:{self.object_id} | {self.day} {self.time_slot} {state}"
