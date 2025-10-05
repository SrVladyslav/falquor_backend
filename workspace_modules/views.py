from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from users.models import Account
from django.utils import timezone
from django.utils.decorators import method_decorator
from core.tasks.email_tasks import send_email
from workspace_modules.services import provision_workspace_one_to_one
from workspace_modules.serializers import WorkspaceCreateSerializer
from rest_framework.decorators import action


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
        account = request.user
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
