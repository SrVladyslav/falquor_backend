from django.db import models
from sidebar_nav.models.base import SidebarManifest
from core.models import BaseNanoID, BaseTimestamp
from decimal import Decimal


class BaseModule(BaseTimestamp, BaseNanoID):
    name = models.CharField(max_length=64, null=False, blank=False)
    description = models.TextField(max_length=256, null=True, blank=True)
    sidebar_manifest = models.ForeignKey(
        SidebarManifest, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Pricing in Euros
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    grace_days_period = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class Workspace(BaseModule):
    class WorkspaceType(models.TextChoices):
        MECHANICAL_WORKSHOP = "MECHANICAL_WORKSHOP", "Mechanical Workshop"
        HORECA = "HORECA", "Horeca"
        OTHER = "OTHER", "Other"

    workspace_type = models.CharField(max_length=32, choices=WorkspaceType.choices)

    class Meta:
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"
        ordering = ["-created_at", "name"]

    def __str__(self):
        return f"{self.name or self.wid} | {self.workspace_type}"

    @property
    def base_price(self) -> Decimal:
        base = self.price or Decimal("0")
        modules_total = sum((m.price or Decimal("0")) for m in self.modules.all())
        return base + modules_total


class WorkspaceModule(BaseModule):
    parent_module = models.ForeignKey(
        Workspace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modules",
    )

    class Meta:
        verbose_name = "Workspace Module"
        verbose_name_plural = "Workspace Modules"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name or self.wid}"
