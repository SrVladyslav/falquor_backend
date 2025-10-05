from django import forms
from django.contrib.contenttypes.models import ContentType
from core.models import BusinessOrganization
from workspace_modules.models.base import Workspace


class WorkspaceAdminForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        allowed_cts = []
        for ct in ContentType.objects.all():
            model_cls = ct.model_class()
            if model_cls is None:
                continue  # skip dangling contenttypes
            if issubclass(model_cls, BusinessOrganization):
                allowed_cts.append(ct.pk)

        self.fields["main_business_ct"].queryset = ContentType.objects.filter(
            pk__in=allowed_cts
        )
