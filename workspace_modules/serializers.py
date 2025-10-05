from rest_framework import serializers
from typing import Any

# Incoming payload structure from your frontend (cleaned)
# {
#   "business": {
#       "business_name": "Natir Iberica",
#       "business_type": "mechanical_hanical_workshop",
#       "tax_id": "B-1234556798",
#       "email": "admin@natir.es",
#       "phone": "+3469696..."
#   },
#   "address": {
#       "address": "C/ Bony 21",
#       "street": null,
#       "postal_code": "46016",
#       "city": "Valencia",
#       "state": "",
#       "country": "Spain"
#   },
#   "language": {
#       "preferredLocale": null,
#   },
#   "addons": { "warehouse": true, "workingHours": true }
# }


# Base serializers
class BusinessSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=100)
    business_type = serializers.CharField(max_length=64)  # we will normalize/match
    email = serializers.EmailField(max_length=100)
    tax_id = serializers.CharField(max_length=50, required=True)
    phone = serializers.CharField(max_length=100, required=False, allow_blank=True)
    fax = serializers.CharField(max_length=100, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)


class AddressSerializer(serializers.Serializer):
    country = serializers.CharField(max_length=100, required=True)
    city = serializers.CharField(max_length=100, required=True)
    address = serializers.CharField(max_length=100, required=True)
    street = serializers.CharField(
        max_length=100, required=False, allow_null=True, allow_blank=True
    )
    postal_code = serializers.CharField(max_length=15, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)


class LanguageSerializer(serializers.Serializer):
    preferredLocale = serializers.CharField(
        max_length=16, required=False, allow_null=True, allow_blank=True
    )
    tz = serializers.CharField(
        max_length=64, required=False, allow_null=True, allow_blank=True
    )
    weekStart = serializers.CharField(
        max_length=16, required=False, allow_null=True, allow_blank=True
    )


class AddonsSerializer(serializers.Serializer):
    warehouse = serializers.BooleanField(required=False, default=False, allow_null=True)
    workingHours = serializers.BooleanField(
        required=False, default=False, allow_null=True
    )


class WorkspaceCreateSerializer(serializers.Serializer):
    business = BusinessSerializer()
    address = AddressSerializer()
    language = LanguageSerializer(required=False)
    addons = AddonsSerializer(required=False)

    def validate_business(self, value: dict[str, Any]) -> dict[str, Any]:
        # Accept minor typos/variants and normalize to canonical keys
        # e.g. "mechanical_hanical_workshop" -> "MECHANICAL_WORKSHOP"
        raw = (value.get("business_type") or "").strip().lower()

        aliases = {
            "mechanical_workshop": "MECHANICAL_WORKSHOP",
            "workshop": "MECHANICAL_WORKSHOP",
            "horeca": "HORECA",
            "restaurant": "HORECA",
            "bar": "HORECA",
            "other": "OTHER",
        }
        normalized = aliases.get(raw)
        if not normalized:
            raise serializers.ValidationError(f"Unknown business_type '{raw}'.")
        value["business_type"] = normalized
        return value
