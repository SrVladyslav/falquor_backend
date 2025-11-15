from django.db import models
from core.models import BaseTimestamp
from mechanic_workshop.models.base import MechanicWorkshop
from django.utils import timezone
from users.models import WorkspaceMember


class WorkerVacationInformation(models.Model):
    # General information
    total_leave_days = models.PositiveIntegerField(
        default=22
    )  # Total allowed leave days per year
    mechanical_workshop = models.ForeignKey(
        MechanicWorkshop, on_delete=models.CASCADE, related_name="vacation_information"
    )
    workshop_worker = models.ForeignKey(
        WorkspaceMember,
        on_delete=models.CASCADE,
        related_name="vacation_information",
    )

    @property
    def leave_days_taken(self):
        current_year = timezone.now().year
        return self.leave_days.filter()

    class Meta:
        verbose_name = "Vacation Information"
        verbose_name_plural = "Vacation Information"

    def __str__(self):
        return f"{self.mechanical_workshop} | {self.worshop_worker} ({self.total_leave_days})"


class LeaveDay(BaseTimestamp):
    requested_by = models.ForeignKey(
        WorkerVacationInformation, on_delete=models.CASCADE, related_name="leave_days"
    )
    accepted_by = models.ForeignKey(
        WorkspaceMember,
        on_delete=models.CASCADE,
        related_name="accepted_leave_days",
        blank=True,
        null=True,
    )
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_half_day = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True, max_length=1024)
    is_rejected = models.BooleanField(default=False)
    rejection_reason = models.TextField(null=True, blank=True, max_length=256)

    @property
    def worker(self):
        return self.requested_by.workshop_worker

    @property
    def is_accepted(self):
        return self.accepted_by is not None

    class Meta:
        verbose_name = "Leave Day"
        verbose_name_plural = "Leave Days"

    def __str__(self):
        return f"{self.worker} ({self.start_date} - {self.end_date})"
