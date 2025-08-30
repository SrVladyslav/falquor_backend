from django.contrib import admin
from django.db import models
from sidebar_nav.models.base import SidebarManifest
from core.admin_widgets import PrettyJSONWidget

# admin.site.register(SidebarManifest)


@admin.register(SidebarManifest)
class SidebarManifestAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.JSONField: {
            "widget": PrettyJSONWidget(
                attrs={"rows": 25, "style": "font-family:monospace"}
            )
        },
    }
