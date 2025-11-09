from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from django.utils import timezone
from users.models import Account
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from users.models import UserToken
from rest_framework.permissions import IsAuthenticated
from users.utils.accounts import create_customer_account
from customers.models import WorkshopCustomer
from customers.serializers import WorkshopCustomerCreateSerializer
from customers.customer_mapper import map_front_to_customer
from django.shortcuts import get_object_or_404
from workspace_modules.models.base import Workspace


class WorkshopEntrancesViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        ws_id = request.query_params.get("wsId")
        print("wsId: ", ws_id)

        if not ws_id:
            return Response(
                {"error": "Missing wsId query parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        print("Creating entrance: ", request.data)
        if not (customer := request.data.get("customer")):
            return Response(
                {"error": "Missing customer data"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        print("customer: ", customer)
        customer_data = map_front_to_customer(customer)
        print("customer_data: ", customer_data)
        # Obtain the workspace from the query parameter
        # TODO: Validate that this workspace is allowed to be updated by the owner
        workspace = get_object_or_404(Workspace, pk=ws_id)
        mechanic_workshop = workspace.main_business
        print("mechanic_workshop: ", mechanic_workshop)
        customer_serializer = WorkshopCustomerCreateSerializer(
            data=customer_data, context={"mechanic_workshop": mechanic_workshop}
        )
        if not customer_serializer.is_valid():
            print("Invalid customer: ", customer_serializer.errors)
            return Response(
                {"error": customer_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cu = customer_serializer.save()
        print("Created customer: ", cu)
        # create_customer_account(
        #     email=request.data.get("email"),
        #     data=request.data,
        # )
        return Response(
            {"detail": "OK"},
            status=status.HTTP_201_CREATED,
        )
