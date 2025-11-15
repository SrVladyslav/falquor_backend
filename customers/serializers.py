from rest_framework import serializers
from users.models import WorkspaceMember, Account


class WorkshopCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceMember
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
        model = WorkspaceMember
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
        workspace = self.context.get("workspace")
        if mechanic_workshop is None:
            raise serializers.ValidationError(
                {
                    "mechanic_workshop": "Missing mechanic_workshop in serializer context."
                }
            )
        if workspace is None:
            raise serializers.ValidationError(
                {"workspace": "Missing workspace in serializer context."}
            )

        email = validated_data["email"]
        # Check if we have an Account for this email, if not, just create it
        account, account_created = Account.objects.get_or_create(email=email)
        print("account_created: ", account_created, "account: ", account)

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

        obj, created = WorkspaceMember.objects.update_or_create(
            workspace=workspace,
            account=account,
            email=email,
            defaults=defaults,
        )

        # Just to know if it was created or updated
        self._created = created
        return obj
