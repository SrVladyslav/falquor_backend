# core/admin_site.py
from __future__ import annotations

from typing import Dict, List, Tuple, Type, Iterable
from django.contrib import admin
from django.contrib.admin import AdminSite, ModelAdmin
from django.core.exceptions import FieldDoesNotExist

# ==== Import your models here (centralized) ====
from mechanic_workshop.models.base import MechanicWorkshop
from mechanic_workshop.models.service import LoanerCar, LoanerCarHistory
from mechanic_workshop.models.vacations import WorkerVacationInformation, LeaveDay
from mechanic_workshop.models.appointments import Appointment
from mechanic_workshop.models.warehouses import (
    Warehouse,
    WarehouseInventory,
    WarehouseItem,
)
from mechanic_workshop.models.workorders import (
    WorkOrder,
    WorkOrderAssignment,
    Discount,
    ReplacementPart,
    WorkOrderDamageSketch,
)
from mechanic_workshop.models.vehicles import CustomerVehicle
from django.urls import reverse

PREFERRED_GROUP_ORDER = [
    "Base",
    "Service",
    "Vacations",
    "Appointments",
    "Warehouses",
    "Workorders",
    "Customer Vehicles",
    "Other",
]


class CoreAdminSite(AdminSite):
    site_header = "ICARSIA Admin"
    site_title = "ICARSIA Admin"
    index_title = "Control panel"

    def get_app_list(self, request, app_label: str | None = None):
        """
        If `app_label` is provided, keep Django's default behavior for app_index.
        Otherwise, return a synthetic app list grouped by our `admin_group`.
        """
        if app_label is not None:
            # Keep default app-level page behavior
            return super().get_app_list(request, app_label)

        # Build groups -> models (each group is a "fake app")
        groups: Dict[str, Dict] = {}

        for model, model_admin in self._registry.items():
            if not model_admin.has_view_permission(request):
                continue

            group = getattr(model_admin, "admin_group", "Other")
            label = getattr(
                model_admin, "menu_label", model._meta.verbose_name_plural.title()
            )

            # Initialize group "app"
            key = group
            if key not in groups:
                groups[key] = {
                    "name": group,  # display name of the group
                    "app_label": key.lower().replace(" ", "_"),
                    "app_url": None,  # prevent header link confusion
                    "has_module_perms": True,
                    "models": [],
                }

            # Permissions
            perms = {
                "add": model_admin.has_add_permission(request),
                "change": model_admin.has_change_permission(request),
                "delete": model_admin.has_delete_permission(request),
                "view": model_admin.has_view_permission(request),
            }

            info = (model._meta.app_label, model._meta.model_name)
            changelist_url = reverse(f"{self.name}:{info[0]}_{info[1]}_changelist")
            add_url = (
                reverse(f"{self.name}:{info[0]}_{info[1]}_add")
                if perms["add"]
                else None
            )

            # Create a fresh dict (no reuse) to avoid any accidental mutation
            model_entry = {
                "name": label,  # use your exact menu_label
                "object_name": model._meta.object_name,
                "perms": perms,
                "admin_url": changelist_url,
                "add_url": add_url,
                "view_only": not (perms["add"] or perms["change"] or perms["delete"]),
            }
            groups[key]["models"].append(model_entry)

        # Sort models by label inside each group
        for g in groups.values():
            g["models"].sort(key=lambda m: m["name"].lower())

        # --- choose group ordering ---
        # 1) Fixed order if you want it:
        ordered_groups: List[Dict] = []
        for gname in PREFERRED_GROUP_ORDER:
            if gname in groups:
                ordered_groups.append(groups[gname])
        # 2) Any remaining groups alphabetically (fallback)
        remaining = [v for k, v in groups.items() if k not in PREFERRED_GROUP_ORDER]
        ordered_groups.extend(sorted(remaining, key=lambda a: a["name"].lower()))

        # # DEBUG: uncomment to log mapping (helps detect mismatches)
        # print("=== Admin menu mapping ===")
        # for g in ordered_groups:
        #     print(f"[{g['name']}]")
        #     for m in g["models"]:
        #         print(f"  - {m['name']} -> {m['admin_url']}")

        return ordered_groups


# Single instance to plug in urls.py
admin_site = CoreAdminSite(name="core_admin")

# ---------------- Utilities ----------------


def _filter_existing_fields(model, names: Iterable[str]) -> Tuple[str, ...]:
    """
    Keep only names that are either:
      - an actual model field, or
      - a callabe/attr that ModelAdmin can resolve later (we only safely detect model fields here).
    This prevents admin.E108/E116 crashes when a name is wrong.
    """
    if not names:
        return tuple()
    keep: List[str] = []
    for n in names:
        if not isinstance(n, str):
            # Django expects strings here; callables should be defined as methods on the admin class.
            continue
        try:
            # If it exists as a model field, keep it
            model._meta.get_field(n)
            keep.append(n)
        except FieldDoesNotExist:
            # Not a model field; we allow it (might be a @admin.display on the admin class),
            # but to avoid E108 we only keep it if it's clearly a relation path "fk__field" or
            # you can comment next 2 lines to be stricter:
            if "__" in n:  # allow related lookups e.g., "customer__full_name"
                keep.append(n)
            # else: skip to avoid admin.E108
            # If you prefer to keep all and rely on your admin methods, comment the checks above.
            # keep.append(n)
            pass
    return tuple(keep)


def register(
    model,
    *,
    group: str,
    menu_label: str | None = None,
    list_display: Tuple[str, ...] | None = None,
    search_fields: Tuple[str, ...] | None = None,
    list_filter: Tuple[str, ...] | None = None,
    ordering: Tuple[str, ...] | None = None,
    readonly_fields: Tuple[str, ...] | None = None,
):
    """
    Compact helper to register ModelAdmins in our custom admin_site with a 'group'.
    - Ensures __module__ is correct (prevents weird paths like django.forms.widgets.*)
    - Validates list_display/list_filter fields exist to avoid admin.E108/E116.
    """
    attrs = {
        "__module__": __name__,  # <- important to avoid weird module paths
        "admin_group": group,  # used by the grouped index
    }
    if menu_label:
        attrs["menu_label"] = menu_label

    if list_display:
        attrs["list_display"] = _filter_existing_fields(model, list_display)
    if search_fields:
        # search_fields allow lookups like "fk__field", so we do not filter strictly here
        attrs["search_fields"] = tuple(search_fields)
    if list_filter:
        attrs["list_filter"] = _filter_existing_fields(model, list_filter)
    if ordering:
        attrs["ordering"] = tuple(ordering)
    if readonly_fields:
        attrs["readonly_fields"] = tuple(readonly_fields)

    admin_cls: Type[ModelAdmin] = type(f"{model.__name__}Admin", (ModelAdmin,), attrs)
    admin_site.register(model, admin_cls)


# --------------- Registrations (sections) ---------------

# Base
register(
    MechanicWorkshop,
    group="Base",
    menu_label="Mechanic Workshops",
    search_fields=("business_name", "document_number"),
)
# Service
register(
    LoanerCarHistory,
    group="Service",
    menu_label="Loaner Car History",
    list_display=("car", "customer", "start_date", "end_date"),
    list_filter=("start_date", "end_date"),
)
register(
    LoanerCar,
    group="Service",
    menu_label="Loaner Cars",
    list_display=("plate", "brand", "model"),
    search_fields=("plate", "brand", "model"),
)

# Vacations
register(
    WorkerVacationInformation,
    group="Vacations",
    menu_label="Vacation Info",
    list_display=("worker", "year", "days_total", "days_taken"),
    list_filter=("year",),
)
register(
    LeaveDay,
    group="Vacations",
    menu_label="Leave Days",
    list_display=("worker", "date", "reason"),
    list_filter=("date",),
)

# Appointments
register(
    Appointment,
    group="Appointments",
    menu_label="Appointments",
    list_display=("customer", "scheduled_at", "status"),
    list_filter=("status", "scheduled_at"),
    search_fields=("customer__full_name", "customer__email"),
)

# Warehouses
register(
    Warehouse,
    group="Warehouses",
    menu_label="Warehouses",
    list_display=("name",),
    search_fields=("name",),
)
register(
    WarehouseInventory,
    group="Warehouses",
    menu_label="Inventory",
    list_display=("warehouse", "sku", "qty"),
    search_fields=("sku", "warehouse__name"),
    list_filter=("warehouse",),
)
register(
    WarehouseItem,
    group="Warehouses",
    menu_label="Items",
    list_display=("sku", "name", "brand"),
    search_fields=("sku", "name", "brand"),
)

# Workorders
register(
    WorkOrder,
    group="Workorders",
    menu_label="Work Orders",
    list_display=("id", "customer", "vehicle", "status", "created_at"),
    list_filter=("status", "created_at"),
    search_fields=("customer__full_name", "vehicle__plate"),
)
register(
    WorkOrderAssignment,
    group="Workorders",
    menu_label="Assignments",
    list_display=("work_order", "assignee", "role", "created_at"),
    list_filter=("role",),
)
register(
    Discount,
    group="Workorders",
    menu_label="Discounts",
    list_display=("work_order", "name", "amount"),
    search_fields=("name",),
)
register(
    ReplacementPart,
    group="Workorders",
    menu_label="Replacement Parts",
    list_display=("work_order", "name", "sku", "qty"),
    search_fields=("name", "sku"),
)
register(
    WorkOrderDamageSketch,
    group="Workorders",
    menu_label="Damage Sketches",
    list_display=("work_order", "view", "created_at"),
    list_filter=("view", "created_at"),
)

# Customer Vehicles
# register(
#     WorkshopCustomer,
#     group="Customers",
#     menu_label="Customers",
# )
register(
    CustomerVehicle,
    group="Customers",
    menu_label="CustomersVehicles",
)
