from django.db import models
from core.models import BaseTimestamp, BaseUUID, MarketingSettings
from mechanic_workshop.models.base import MechanicWorkshop
from users.models import Account, WorkspaceMember
from django.db.models import Q, CheckConstraint


class CustomerExtraData(models.Model):
    customer = models.ForeignKey(
        WorkspaceMember, on_delete=models.CASCADE, related_name="extra_data"
    )
    version = models.IntegerField(default=1)
    comments = models.TextField(null=True, blank=True, max_length=1000)
