from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from django.utils import timezone
from users.models import Account
from django.db import transaction
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from users.models import UserToken
from rest_framework.permissions import IsAuthenticated
from users.utils.accounts import create_customer_account
from customers.serializers import WorkshopCustomerCreateSerializer
from customers.customer_mapper import map_front_to_customer
from django.shortcuts import get_object_or_404
from workspace_modules.models.base import Workspace
from workspace_modules.utils.memberships import is_workspace_member
from users.mappers import map_workshop_customer_to_account
from mechanic_workshop.models.vehicles import CustomerVehicle
from mechanic_workshop.serializers.vehicles import (
    CustomerVehicleWorkshopListSerializer,
    CustomerVehicleCreateSerializer,
)
from mechanic_workshop.serializers.workorders import WorkorderCreateSerializer
from users.models import WorkspaceMember
from mechanic_workshop.models.base import MechanicWorkshop
from mechanic_workshop.mappers.workorder import map_frontend_to_workorder
import json


class WorkshopEntrancesViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
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

        if not (workorder_data := request.data.get("workorder", None)):
            return Response(
                {"error": "Missing workorder data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ========================================================================
        # 1) Create the customer account or connect to the existing one
        # ========================================================================
        customer_data = map_front_to_customer(customer)
        is_vehicle_owner = customer_data.get("is_vehicle_owner", False)
        print("customer_data: ", customer_data)
        # Obtain the workspace from the query parameter
        workspace = get_object_or_404(Workspace, pk=ws_id)
        caller_ws_member, caller_is_member = is_workspace_member(
            account=caller, workspace=workspace
        )
        if not caller_is_member:
            return Response(
                {"error": "You are not a member of this workspace"},
                status=status.HTTP_403_FORBIDDEN,
            )

        mechanic_workshop = workspace.main_business
        print("\n mechanic_workshop: ", mechanic_workshop)
        customer_serializer = WorkshopCustomerCreateSerializer(
            data=customer_data,
            context={
                "caller": caller,
                "mechanic_workshop": mechanic_workshop,
                "workspace": workspace,
            },
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
        vehicle_data["owner"] = customer_model.uuid if is_vehicle_owner else None
        vehicle_data["authorized_people"] = [customer_model.uuid]
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
        # ========================================================================
        # 3) Create the new Workorder
        # ========================================================================
        # Prepare the damage data
        damage = workorder_data.get("damage", {})
        length = 0
        for v in damage.values():
            d = json.dumps(v)
            length += len(d)

        if length > 15000:
            return Response(
                {"error": "The damage sketches are too large."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mapped_damage = map_frontend_to_workorder(front=workorder_data)
        mapped_damage["customer_vehicle"] = vehicle_model.pk
        mapped_damage["workshop"] = mechanic_workshop.uuid
        mapped_damage["attended_by"] = caller_ws_member.uuid
        mapped_damage["vehicle_presenter"] = customer_model.uuid
        mapped_damage["customer_telephone"] = customer_model.phone

        damage_serializer = WorkorderCreateSerializer(data=mapped_damage)
        if not damage_serializer.is_valid():
            return Response(
                {"error": damage_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        damage_model = damage_serializer.save()
        print("Damage model: ", damage_model)
        print("\n DAMAGE LENGTH: ", length)

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
            workspace__members__account=account,
            workspace__members__is_active=True,
            workspace__members__role__in=[
                WorkspaceMember.WorkspaceRole.OWNER,
                WorkspaceMember.WorkspaceRole.ADMIN,
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
