from django.contrib import admin

from workspace_modules.models.base import (
    Workspace,
    WorkspaceModule,
    WorkspaceMembership,
)
from workspace_modules.forms import WorkspaceAdminForm


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    form = WorkspaceAdminForm
    list_display = (
        "wid",
        "workspace_type",
        "main_business",
        "is_active",
        "created_at",
    )
    readonly_fields = ("wid",)  # se ve en la vista de edición (tras guardar)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "wid",  # se mostrará readonly tras guardar
                    # "name",
                    "short_name",
                    "workspace_type",
                    "price",
                    "expires_at",
                    "grace_days_period",  # ojo al typo, comento abajo
                    "sidebar_manifest",
                    "main_business_ct",
                    "main_business_id",
                    "time_zone",
                    "is_active",
                    "is_deleted",
                )
            },
        ),
    )


admin.site.register(WorkspaceModule)
admin.site.register(WorkspaceMembership)
