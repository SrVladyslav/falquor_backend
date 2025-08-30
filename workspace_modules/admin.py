from django.contrib import admin

from workspace_modules.models.base import Workspace, WorkspaceModule


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("wid", "name", "workspace_type", "is_active", "created_at")
    readonly_fields = ("wid",)  # se ve en la vista de edición (tras guardar)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "wid",  # se mostrará readonly tras guardar
                    "name",
                    "workspace_type",
                    "description",
                    "price",
                    "expires_at",
                    "grace_days_period",  # ojo al typo, comento abajo
                    "sidebar_manifest",
                    "is_active",
                    "is_deleted",
                )
            },
        ),
    )


admin.site.register(WorkspaceModule)
