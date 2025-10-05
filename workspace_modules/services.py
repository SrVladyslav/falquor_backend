from typing import Any
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.utils.text import slugify
from django.utils import timezone

from workspace_modules.models.base import (
    Workspace,
    WorkspaceMembership,
    WorkspaceModule,
)
from mechanic_workshop.models.base import MechanicWorkshop
from users.models import WorkspaceMember
from sidebar_nav.models.base import SidebarManifest

# from horeca.models import Horeca

# If you have WeekWorkingHours creator, import it
# from scheduling.services import init_default_week_hours


def _build_mechanic_payload(
    biz: dict[str, Any], addr: dict[str, Any], lang: dict[str, Any]
) -> dict[str, Any]:
    """Merge business + address + language into MechanicWorkshop fields."""
    out = {
        "business_name": biz.get("business_name"),
        "description": biz.get("description") or "",
        "tax_id": biz.get("tax_id") or "",
        "email": biz.get("email"),
        "phone": biz.get("phone") or "",
        "fax": biz.get("fax") or "",
        "website": biz.get("website") or "",
        "address": (addr or {}).get("address") or "",
        "street": (addr or {}).get("street") or "",
        "postal_code": (addr or {}).get("postal_code") or "",
        "city": (addr or {}).get("city") or "",
        "state": (addr or {}).get("state") or "",
        "country": (addr or {}).get("country") or "",
        # Our abstract has time_zone; prefer language.tz fallback to default
        "time_zone": (lang or {}).get("tz") or "Europe/Madrid",
        # Specific MechanicWorkshop defaults
        "has_towing_service": False,
        "has_car_service": False,
    }
    return out


def _get_addon_price(addon_name: str, promo_code: str = None) -> float:

    return float(0)


def _enable_addons(workspace: Workspace, addons: dict[str, Any]) -> None:
    """
    Create WorkspaceModule rows (or any other bootstrap) based on addons.
    """
    if not addons:
        return

    now = timezone.now()

    if addons.get("warehouse"):
        WorkspaceModule.objects.create(
            name="warehouse",
            parent_module=workspace,
            price=_get_addon_price(addon_name="warehouse"),  # Add price here
            contract_starts_at=now,
            expires_at=None,
            is_active=True,
        )

    if addons.get("workingHours"):
        WorkspaceModule.objects.create(
            name="working_hours",
            parent_module=workspace,
            price=_get_addon_price(addon_name="working_hours"),  # Add price here
            contract_starts_at=now,
            expires_at=None,
            is_active=True,
        )


@transaction.atomic
def provision_workspace_one_to_one(
    *,
    user,
    payload: dict[str, Any],
) -> Workspace:
    """
    Transactionally create:
    - Concrete business (MechanicWorkshop or Horeca...),
    - Workspace (GFK -> business),
    - Membership for the creator (OWNER + can_manage_billing),
    - Addon modules if requested,
    - Link back business.workspace = workspace (since your BusinessOrganization has FK workspace).
    """
    business = payload.get("business") or {}
    address = payload.get("address") or {}
    language = payload.get("language") or {}
    addons = payload.get("addons") or {}
    short_name = payload.get("short_name") or None

    btype = business["business_type"]  # normalized by serializer

    # 1) Create business concrete
    if btype == "MECHANICAL_WORKSHOP":
        create_kwargs = _build_mechanic_payload(
            biz=business, addr=address, lang=language
        )
        biz = MechanicWorkshop.objects.create(**create_kwargs)
    elif btype == "HORECA":
        # TODO: implement Horeca creation mapping if you have the model
        # biz = Horeca.objects.create(...)
        raise NotImplementedError("HORECA creation not implemented yet.")
    else:
        # If you plan an 'Other' model, create it here; else, block
        raise ValueError("Unsupported business_type")

    if not biz:
        print("Unsupported business_type: ", btype)
        raise ValueError("Unsupported business_type")

    # 2) Build GFK
    ct = ContentType.objects.get_for_model(biz.__class__)

    # 3) Create workspace pointing to the business via GFK
    ws_name = short_name or business.get("business_name") or "Workspace"
    workspace = Workspace.objects.create(
        short_name=ws_name,
        main_business_ct=ct,
        main_business_id=biz.pk,
        # workspace_type will be derived in save()
    )

    # 3.5) Add the default manifest for the workspace
    if workspace_manifest := SidebarManifest.objects.filter(
        name="DEFAULT_MANIFEST"
    ).first():
        workspace.sidebar_manifest = workspace_manifest
        workspace.save(update_fields=["sidebar_manifest"])

    # 4) Link back business.workspace (your abstract has optional FK to Workspace)
    #    Useful for reverse lookups and admin tooling
    biz.workspace = workspace
    biz.save(update_fields=["workspace"])

    # 5) Creator membership (OWNER + can_manage_billing)
    WorkspaceMembership.objects.create(
        workspace=workspace,
        user=user,
        role=WorkspaceMembership.Roles.OWNER,
        is_active=True,
        can_manage_billing=True,
    )

    # 6) Enable addons as modules
    _enable_addons(workspace, addons)

    # 7) Create the Initial WorkspaceMember for the workshop
    if isinstance(biz, MechanicWorkshop):
        workspace_member, _ = WorkspaceMember.objects.update_or_create(
            workspace=workspace,
            account=user,
            defaults={
                "role": WorkspaceMember.WorkspaceRole.OWNER,
                "is_active": True,
                "is_owner": True,
                "is_admin": True,
                "invited_by": user,  # Meaning that it's the owner
            },
        )
        print("Team Member created: ", workspace_member)

    return workspace
