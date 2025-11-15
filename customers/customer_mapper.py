from users.models import WorkspaceMember


def map_front_to_customer(front: dict[str, str]) -> dict[str, str]:
    """Map the data from the front-end to the Customer model."""

    allowed_document_types = WorkspaceMember.DocumentType.values
    tax_objects: dict[str, str] = front.get("tax_id", {})
    doc_type: str = tax_objects.get("document_type")
    if doc_type not in allowed_document_types:
        doc_type = WorkspaceMember.DocumentType.PASSPORT

    return {
        "name": front.get("name"),
        "surname": front.get("surname"),
        "email": front.get("email"),
        "phone": front.get("phone"),
        "postal_code": front.get("postal_code"),
        "country": front.get("country"),
        "city": front.get("city"),
        "address": front.get("address"),
        "tax_id": tax_objects.get("value"),
        "document_type": doc_type,
        "is_vehicle_owner": front.get("is_vehicle_owner"),
    }
