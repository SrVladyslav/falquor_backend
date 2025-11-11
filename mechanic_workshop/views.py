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
from workspace_modules.models.base import Workspace, WorkspaceMembership
from workspace_modules.utils.memberships import is_workspace_member
from users.mappers import map_workshop_customer_to_account
from mechanic_workshop.models.vehicles import CustomerVehicle
from mechanic_workshop.serializers.vehicles import (
    CustomerVehicleWorkshopListSerializer,
    CustomerVehicleCreateSerializer,
)
from mechanic_workshop.models.base import MechanicWorkshop


class WorkshopEntrancesViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        caller = request.user
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

        if not (vehicle_data := request.data.get("vehicle", None)):
            return Response(
                {"error": "Missing vehicle data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ========================================================================
        # 1) Create the customer account or connect to the existing one
        # ========================================================================
        customer_data = map_front_to_customer(customer)
        print("customer_data: ", customer_data)
        # Obtain the workspace from the query parameter
        workspace = get_object_or_404(Workspace, pk=ws_id)
        if not is_workspace_member(caller, workspace):
            return Response(
                {"error": "You are not a member of this workspace"},
                status=status.HTTP_403_FORBIDDEN,
            )

        mechanic_workshop = workspace.main_business
        print("\n mechanic_workshop: ", mechanic_workshop)
        customer_serializer = WorkshopCustomerCreateSerializer(
            data=customer_data, context={"mechanic_workshop": mechanic_workshop}
        )
        if not customer_serializer.is_valid():
            print("Invalid customer: ", customer_serializer.errors)
            return Response(
                {"error": customer_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        customer_model = customer_serializer.save()
        # We also create a basic account for the user, so we can handle some basic information about it
        account, account_created = map_workshop_customer_to_account(customer_model)
        print("Created customer: ", customer_model)
        print("Created account: ", account, "TRUE" if account_created else "FALSE")

        # ========================================================================
        # 2) Create the Vehicle information
        # ========================================================================
        vehicle_data["customer"] = customer_model.uuid
        vehicle_data["main_workshop"] = mechanic_workshop.uuid
        vehicle_serializer = CustomerVehicleCreateSerializer(data=vehicle_data)
        print("main workshop", mechanic_workshop, type(mechanic_workshop))
        if not vehicle_serializer.is_valid():
            print("Invalid vehicle: ", vehicle_serializer.errors)
            return Response(
                {"error": vehicle_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vehicle_model = vehicle_serializer.save()
        print("Created vehicle: ", vehicle_model)
        # ========================================================================
        # 3) Create the new Workorder
        # ========================================================================
        # create_customer_account(
        #     email=request.data.get("email"),
        #     data=request.data,
        # )
        return Response(
            {"detail": "OK"},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="workshop-vehicles")
    def get_workshop_vehicles(self, request):
        account = request.user
        workshop_id = request.query_params.get("wsId")
        print("account: ", account)
        print("workshop_id: ", workshop_id)

        workshop = MechanicWorkshop.objects.filter(
            workspace__memberships__user=account,
            workspace__memberships__is_active=True,
            workspace__memberships__role__in=[
                WorkspaceMembership.Roles.OWNER,
                WorkspaceMembership.Roles.ADMIN,
                WorkspaceMembership.Roles.MANAGER,
                # TODO: Add more roles here
            ],
            workspace__wid=workshop_id,
        ).first()
        print("workshop: ", workshop)

        vehicles = CustomerVehicleWorkshopListSerializer(
            workshop.customer_vehicles.all(), many=True
        )
        print("vehicles: ", vehicles)
        return Response(
            {"detail": "OK", "vehicles": vehicles.data},
            status=status.HTTP_200_OK,
        )
