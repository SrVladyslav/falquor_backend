from users.models import Account
from workspace_modules.models.base import Workspace
from users.models import WorkspaceMember


def is_workspace_member(
    account: Account, workspace: Workspace
) -> tuple[WorkspaceMember, bool]:
    """Check if a user is a member of a workspace."""
    workspace_member = WorkspaceMember.objects.filter(
        workspace=workspace, account=account, is_active=True
    ).first()

    if workspace_member is None:
        return None, False
    return workspace_member, True
