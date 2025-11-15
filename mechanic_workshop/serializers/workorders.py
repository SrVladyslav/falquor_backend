from rest_framework import serializers
from mechanic_workshop.models.workorders import WorkOrder
from mechanic_workshop.models.vehicles import CustomerVehicle


class WorkorderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = [
            "workshop",
            "customer_vehicle",
            "vehicle_presenter",
            "attended_by",
            "damage",
            "description",
            "observations",
            "start_mileage",
            "start_fuel_level",
            "lights",
            "allow_repair_vehicle",
            "client_wants_replacements_back",
            "vehicle_sketch_model",
        ]
