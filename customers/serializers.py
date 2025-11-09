from rest_framework import serializers
from customers.models import WorkshopCustomer


class WorkshopCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopCustomer
        fields = [
            "uuid",
            "created_at",
            "updated_at",
            "name",
            "surname",
            "alias",
            "email",
            "phone",
            "birth_date",
            "document_number",
            "document_type",
            "address",
            "postal_code",
            "city",
            "state",
            "country",
        ]


class WorkshopCustomerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopCustomer
        fields = [
            "name",
            "surname",
            "email",
            "phone",
            "postal_code",
            "country",
            "city",
            "address",
            "tax_id",
            "document_type",
        ]

    def validate_email(self, v):
        return (v or "").strip().lower()

    def create(self, validated_data):
        mechanic_workshop = self.context.get("mechanic_workshop")
        if mechanic_workshop is None:
            raise serializers.ValidationError(
                {
                    "mechanic_workshop": "Missing mechanic_workshop in serializer context."
                }
            )

        email = validated_data["email"]

        defaults = {
            "name": validated_data.get("name"),
            "surname": validated_data.get("surname"),
            "phone": validated_data.get("phone"),
            "postal_code": validated_data.get("postal_code"),
            "country": validated_data.get("country"),
            "city": validated_data.get("city"),
            "address": validated_data.get("address"),
            "tax_id": validated_data.get("tax_id"),
            "document_type": validated_data.get("document_type"),
        }

        obj, created = WorkshopCustomer.objects.update_or_create(
            mechanic_workshop=mechanic_workshop,
            email=email,
            defaults=defaults,
        )

        print("Created: ", created)

        # Just to know if it was created or updated
        self._created = created
        return obj
