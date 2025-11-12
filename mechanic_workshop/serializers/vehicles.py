from rest_framework import serializers
from mechanic_workshop.models.vehicles import CustomerVehicle
from django.db import transaction
from users.serializers import UserMinimalSerializer


class CustomerVehicleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerVehicle
        fields = [
            "main_workshop",
            "owner",
            "authorized_people",
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

    def validate(self, attrs):
        vin = attrs.get("vin_number")
        plate = attrs.get("license_plate")
        if not vin and not plate:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "You should provide at least a VIN or a license plate"
                    ]
                }
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        main_workshop = validated_data.get("main_workshop")
        owner = validated_data.get("owner")
        authorized_people = validated_data.get("authorized_people")
        vin_number = validated_data.get("vin_number")
        license_plate = validated_data.get("license_plate")

        if main_workshop is None or authorized_people is None:
            raise serializers.ValidationError(
                {
                    "main_workshop": "Missing mechanic_workshop in serializer context.",
                    "authorized_people": "Missing authorized_people in serializer context.",
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

        # If the vehicle is owned by a person how broutgh the vehicle to the workstation
        if owner:
            defaults["owner"] = owner

        # Update the vehicle
        if vehicle := CustomerVehicle.objects.filter(
            main_workshop=main_workshop,
            vin_number=vin_number,
            license_plate=license_plate,
        ).first():
            for k, v in defaults.items():
                setattr(vehicle, k, v)

            vehicle.authorized_people.add(*authorized_people)
            vehicle.save()

            # Just to know if it was created or updated
            self._created = False
            return vehicle

        vehicle = CustomerVehicle.objects.create(
            main_workshop=main_workshop,
            vin_number=vin_number,
            license_plate=license_plate,
            **defaults,
        )
        vehicle.authorized_people.add(*authorized_people)
        vehicle.save()
        self._created = True
        return vehicle


class CustomerVehicleWorkshopListSerializer(serializers.ModelSerializer):
    authorized_people = UserMinimalSerializer(
        many=True, read_only=True, source="authorized_people_cached"
    )
    owner = UserMinimalSerializer()

    class Meta:
        model = CustomerVehicle
        fields = [
            "id",
            "main_workshop",
            "owner",
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
            "authorized_people",
        ]
