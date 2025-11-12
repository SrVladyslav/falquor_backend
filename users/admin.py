from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import Account, UserToken, WorkspaceMember


class AccountAdmin(UserAdmin):
    list_display = (
        "email",
        "username",
        "otp_code",
        "otp_tries",
        "is_active",
        "is_admin",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
        "preferred_locale",
        "selected_workspace",
        "hide_email",
    )
    search_fields = ("email", "username")
    readonly_fields = ("uuid", "date_joined", "last_login")
    ordering = ("email",)

    filter_horizontal = ()
    list_filter = ()
    fieldsets = (
        (
            "Datos personales",
            {"fields": ("email", "username", "password", "first_name", "last_name")},
        ),
        ("OTP Info", {"fields": ("otp_code", "otp_tries")}),
        (
            "Permisos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "icon_style",
                    "preferred_locale",
                    "selected_workspace",
                    "hide_email",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    @admin.display(description="Is suspended")
    def is_suspended(self, obj):
        return obj.account_suspended


@admin.action(description="Revoke selected tokens")
def revoke_tokens(modeladmin, request, queryset):
    updated = queryset.update(revoked=True)
    modeladmin.message_user(request, f"{updated} token(s) revoked successfully.")


@admin.action(description="Re-activate selected tokens")
def re_activate_tokens(modeladmin, request, queryset):
    updated = queryset.update(revoked=False)
    modeladmin.message_user(request, f"{updated} token(s) re-activated successfully.")


@admin.register(UserToken)
class UserTokenAdmin(admin.ModelAdmin):
    list_display = (
        "user_id_display",
        "user",
        "device",
        "revoked",
        "ip_address",
        "expires_at",
        "created_at",
    )
    list_filter = ("user", "revoked", "expires_at")
    actions = [revoke_tokens, re_activate_tokens]

    @admin.display(description="User ID")
    def user_id_display(self, obj):
        return obj.user.uuid


admin.site.register(Account, AccountAdmin)
admin.site.register(WorkspaceMember)
print("AccountAdmin registered...")
