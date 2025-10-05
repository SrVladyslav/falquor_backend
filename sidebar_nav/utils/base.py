from users.models import Account, WorkspaceMember
from workspace_modules.models.base import Workspace
from typing import Any


def get_manifest(
    account: Account, workspace_member: WorkspaceMember, workspace_id: Workspace
) -> dict[str, Any] | None:
    # Get the workspace manifest
    if not (workspace := Workspace.objects.filter(wid=workspace_id).first()):
        return None

    ws_manifest = workspace.sidebar_manifest.manifest
    print("Workspace Manifest: ", ws_manifest)

    # TODO: Obtain the modules manifest and merge them
    ws_extra_modules = workspace.modules.all()
    print("Extra modules: ", ws_extra_modules)

    # Obtain the user preferences
    meta: dict[str, str] = {
        "manifestId": workspace.sidebar_manifest.uuid,
        "workspaceId": workspace.wid,
    }
    # We use the Account icon style over the generic one
    icon_style = account.icon_style
    # icon_style = workspace_member.icon_style
    if icon_style:
        meta["iconStyle"] = icon_style

    ws_manifest["meta"] = {**ws_manifest.get("meta", {}), **meta}
    # TODO get the accounts user_prefercences

    print("Final Manifest: ", ws_manifest)

    return ws_manifest
