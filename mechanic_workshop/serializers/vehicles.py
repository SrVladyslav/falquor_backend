from rest_framework import serializers
from mechanic_workshop.models.vehicles import CustomerVehicle
from django.db import transaction, IntegrityError


class CustomerVehicleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerVehicle
        fields = [
            "main_workshop",
            "customer",
            # General information
            "brand",
            "model",
            "fuel_type",
            "license_plate",
            "vin_number",
            # Motor information
            "motor_type",
            "motor_brand",
            "cylinders",
            "cylinder_size",
            "engine_power",
        ]
        validators = []

    def validate_vin_number(self, v):
        v = (v or "").strip().upper()
        return v or None

    def validate_license_plate(self, v):
        v = (v or "").strip().upper()
        return v or None

    @transaction.atomic
    def create(self, validated_data):
        main_workshop = validated_data.get("main_workshop")
        customer = validated_data.get("customer")
        vin_number = validated_data.get("vin_number")
        license_plate = validated_data.get("license_plate")

        if main_workshop is None or customer is None:
            raise serializers.ValidationError(
                {
                    "main_workshop": "Missing mechanic_workshop in serializer context.",
                    "customer": "Missing customer in serializer context.",
                }
            )

        defaults: dict[str, str | int] = {
            "brand": validated_data.get("brand"),
            "model": validated_data.get("model"),
            "fuel_type": validated_data.get("fuel_type"),
            "motor_type": validated_data.get("motor_type"),
            "motor_brand": validated_data.get("motor_brand"),
            "cylinders": validated_data.get("cylinders"),
            "cylinder_size": validated_data.get("cylinder_size"),
            "engine_power": validated_data.get("engine_power"),
        }

        # Update the vehicle
        if vehicle := CustomerVehicle.objects.filter(
            main_workshop=main_workshop,
            customer=customer,
            vin_number=vin_number,
            license_plate=license_plate,
        ).first():
            for k, v in defaults.items():
                setattr(vehicle, k, v)
            vehicle.save()

            # Just to know if it was created or updated
            self._created = False
            return vehicle

        vehicle = CustomerVehicle.objects.create(
            main_workshop=main_workshop,
            customer=customer,
            vin_number=vin_number,
            license_plate=license_plate,
            **defaults,
        )
        self._created = True
        return vehicle


class CustomerVehicleWorkshopListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerVehicle
        fields = [
            "id",
            "main_workshop",
            "customer",
            "brand",
            "model",
            "fuel_type",
            "license_plate",
            "vin_number",
            "motor_type",
            "motor_brand",
            "cylinders",
            "cylinder_size",
            "engine_power",
        ]
