from users.models import Account
from workspace_modules.models.base import Workspace, WorkspaceMembership


def is_workspace_member(user: Account, workspace: Workspace) -> bool:
    """Check if a user is a member of a workspace."""
    return WorkspaceMembership.objects.filter(
        workspace=workspace, user=user, is_active=True
    ).exists()
