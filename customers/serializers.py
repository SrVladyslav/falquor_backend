from rest_framework import serializers
from customers.models import WorkshopCustomer


class WorkshopCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopCustomer
        fields = [
            "uuid",
            "created_at",
            "updated_at",
            "first_name",
            "last_name",
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
