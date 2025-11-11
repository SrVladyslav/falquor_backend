from __future__ import annotations
from django.db import models
from sidebar_nav.models.base import SidebarManifest
from core.models import BaseNanoID, BaseTimestamp, BaseUUID
from decimal import Decimal
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q


class BaseModule(BaseTimestamp, BaseNanoID):
    sidebar_manifest = models.ForeignKey(
        SidebarManifest, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Pricing in Euros
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    contract_starts_at = models.DateTimeField(null=True, blank=True)
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

    short_name = models.CharField(
        max_length=128, null=True, blank=True
    )  # Without S.A. etc
    workspace_type = models.CharField(max_length=32, choices=WorkspaceType.choices)

    # Generic 1to1 to the primary business object
    main_business_ct = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to=Q(app_label__in=["mechanic_workshop", "horeca"]),
    )
    main_business_id = models.UUIDField(null=True, blank=True)
    main_business = GenericForeignKey("main_business_ct", "main_business_id")
    time_zone = models.CharField(max_length=100, blank=True, default="Europe/Madrid")

    class Meta:
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"
        ordering = ["-created_at"]
        constraints = [
            # Ensure both parts of the GFK are either set together or both NULL
            # models.CheckConstraint(
            #     check=(
            #         (Q(main_business_ct__isnull=True) & Q(main_business_id__isnull=True)) |
            #         (Q(main_business_ct__isnull=False) & Q(main_business_id__isnull=False))
            #     ),
            #     name="workspace_business_fk_both_or_none",
            # ),
            # Uniqueness: one workspace per given (ct, id)
            models.UniqueConstraint(
                fields=["main_business_ct", "main_business_id"],
                name="workspace_unique_primary_business",
                condition=Q(
                    main_business_ct__isnull=False, main_business_id__isnull=False
                ),
            ),
        ]

    def __str__(self):
        return f"{self.wid} | {self.workspace_type}"

    def save(self, *args, **kwargs):
        if self.main_business_ct:
            model_cls = self.main_business_ct.model_class()
            if model_cls.__name__.upper() == "MECHANICWORKSHOP":
                self.workspace_type = Workspace.WorkspaceType.MECHANICAL_WORKSHOP
            elif model_cls.__name__.upper() == "HORECA":
                self.workspace_type = Workspace.WorkspaceType.HORECA
            else:
                self.workspace_type = Workspace.WorkspaceType.OTHER
        super().save(*args, **kwargs)

    @property
    def base_price(self) -> Decimal:
        base = getattr(self, "price", None) or Decimal("0")
        modules_total = sum((m.price or Decimal("0")) for m in self.modules.all())
        return base + modules_total

    def has_active_membership(self) -> bool:
        return self.memberships.filter(is_active=True).exists()

    # def get_active_membership(self) -> "WorkspaceMembership":
    #     return self.memberships.filter(is_active=True).first()


class WorkspaceModule(BaseModule):
    name = models.CharField(max_length=128, null=True, blank=True)
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


class WorkspaceMembership(BaseUUID, BaseTimestamp):
    class Roles(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        MEMBER = "MEMBER", "Member"
        BILLING = "BILLING", "Billing"

    workspace = models.ForeignKey(
        "Workspace", related_name="memberships", on_delete=models.CASCADE
    )
    # Only for the creator
    user = models.ForeignKey(
        "users.Account", related_name="workspace_memberships", on_delete=models.CASCADE
    )
    role = models.CharField(max_length=16, choices=Roles.choices, default=Roles.MEMBER)
    can_manage_billing = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("workspace", "user")]
        indexes = [
            models.Index(fields=["workspace", "user", "role", "is_active"]),
            models.Index(fields=["workspace", "can_manage_billing"]),
        ]
        verbose_name = "Workspace Membership"
        verbose_name_plural = "Workspace Memberships"
