from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from users.models import Account, WorkspaceMember
from django.utils import timezone
from django.utils.decorators import method_decorator
from core.tasks.email_tasks import send_email
from workspace_modules.services import provision_workspace_one_to_one
from workspace_modules.serializers import (
    WorkspaceCreateSerializer,
    ListManagedWorkspacesSerialzier,
)
from rest_framework.decorators import action
from workspace_modules.models.base import WorkspaceModule
from workspace_modules.models.base import Workspace, WorkspaceMembership


class WorkspaceViewSet(viewsets.ViewSet):
    """
    Creates a workspace + primary business (1:1) and grants creator ownership & billing rights.
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="create-workspace")
    def create_workspace(self, request):
        serializer = WorkspaceCreateSerializer(data=request.data)
        if not serializer.is_valid():
            print("serializer.errors: ", serializer.errors)
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        print("Creating workspace: ", serializer.validated_data)
        workspace = provision_workspace_one_to_one(
            user=request.user,
            payload=serializer.validated_data,
        )
        # Update the user account default workspace:
        account: Account = request.user
        account.selected_workspace = workspace
        account.save()
        print("Created workspace: ", workspace.wid)

        return Response(
            {
                "detail": "OK",
                "workspace": {
                    "id": str(workspace.pk),
                    "wid": workspace.wid,  # from BaseNanoID
                    "workspace_type": workspace.workspace_type,
                    "base_price": str(workspace.base_price),  # keep if you want
                },
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False, methods=["post"], url_path="set-main-wid", url_name="set-main-wid"
    )
    def set_main_wid(self, request):
        """
        Set the main business (concrete) wid for a workspace.
        """
        account: Account = request.user
        wid = request.data.get("new_main_wid")

        if not WorkspaceMember.objects.filter(workspace=wid, account=account).exists():
            return Response(
                {"error": "You are not a member of this workspace"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not (new_main_workspace := Workspace.objects.filter(wid=wid).first()):
            return Response(
                {"error": "Workspace not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        account.selected_workspace = new_main_workspace
        account.save()

        return Response(
            {
                "detail": "OK",
                "workspace": {
                    "wid": new_main_workspace.wid,  # from BaseNanoID
                    "workspace_type": new_main_workspace.workspace_type,
                    "base_price": str(
                        new_main_workspace.base_price
                    ),  # keep if you want
                },
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="get-workspaces",
        url_name="get-workspaces",
    )
    def get_managed_workspaces_min_info(self, request):
        account = request.user
        workspaces = Workspace.objects.filter(
            memberships__user=account,
            memberships__is_active=True,
            memberships__role__in=[
                WorkspaceMembership.Roles.OWNER,
                WorkspaceMembership.Roles.ADMIN,
            ],
        ).distinct()

        serializer = ListManagedWorkspacesSerialzier(workspaces, many=True)
        print("Serializer: ", serializer.data)

        return Response(serializer.data, status=status.HTTP_200_OK)
