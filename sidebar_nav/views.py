from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAuthenticated
from sidebar_nav.utils.base import get_manifest
from users.models import WorkspaceMember


class SidebarNavView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        account = request.user
        workspace_member = None

        workspace_member = WorkspaceMember.objects.filter(
            account=account, workspace__wid=workspace_id
        ).first()

        if not workspace_member:
            return Response(
                {"error": "You are not a member of this workspace"},
                status=status.HTTP_403_FORBIDDEN,
            )

        print("Account: ", account)
        print("Workspace ID: ", workspace_id)
        print("Workspace Member: ", workspace_member)

        manifest = get_manifest(
            account=account,
            workspace_member=workspace_member,
            workspace_id=workspace_id,
        )

        return Response(manifest)
