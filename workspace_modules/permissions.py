from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsWorkspaceMember(BasePermission):
    """
    Allow access only if request.user is member of the target workspace.
    Requires that views resolve `self.get_workspace()` or set `request.workspace`.
    """

    def has_permission(self, request, view):
        # For creation, allow if authenticated (anmd possibly role check below)
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Obj can be a Workspace or any models that has 'workspace' FK
        workspace = (
            getattr(obj, "workspace", None)
            or getattr(view, "get_workspace", lambda: None)()
        )
        if not workspace:
            return False
        return workspace.memberships.filter(user=request.user, is_active=True).exists()


class IsWorkspaceAdmin(BasePermission):
    """
    Requires the user to hold an admin/owner role within the workspace.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        workspace = (
            getattr(obj, "workspace", None)
            or getattr(view, "get_workspace", lambda: None)()
        )
        if not workspace:
            return False
        return workspace.memberships.filter(
            user=request.user, role__in=["OWNER", "ADMIN"], is_active=True
        ).exists()
