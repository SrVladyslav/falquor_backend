from django.db import models
from core.models import BaseUUID, BaseTimestamp


class SidebarScope(models.TextChoices):
    GLOBAL = "GLOBAL", "Global"
    WORKSPACE = "WORKSPACE", "Workspace"
    MODULE = "MODULE", "Module"
    USER = "USER", "User"


class SidebarManifest(BaseUUID, BaseTimestamp):
    name = models.CharField(max_length=64, null=True, blank=True)  # e.g. Customers
    scope = models.CharField(
        max_length=15, choices=SidebarScope.choices, default=SidebarScope.GLOBAL
    )

    # JSON With the sidebar structure
    manifest = models.JSONField(null=True, blank=True)
    version = models.CharField(max_length=8, default="v0.0.1")
    priority = models.PositiveIntegerField(default=10)

    is_active = models.BooleanField(default=True)
    checksum = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "version", "priority", "is_active"],
                name="unique_active_manifest_per_scope_version_priority",
                condition=models.Q(is_active=True),
            )
        ]

    def __str__(self):
        return f"{self.name or 'Unnamed'} | {self.scope} | {self.version} | {self.priority}"
