from typing import Any


def map_frontend_to_workorder(front: dict[str, Any]) -> dict[str, Any]:
    """Map the data from the front-end to the Workorder model."""

    return {
        "damage": front.get("damage", {}),
        "description": front.get("description", ""),
        "observations": front.get("observations", ""),
        "start_mileage": front.get("mileage", None),
        "start_fuel_level": front.get("fuel_level", -1),
        "lights": front.get("lights", ""),
        "vehicle_sketch_model": front.get("vehicle_sketch_model", "BMW_X5"),
        "allow_repair_vehicle": front.get("repair_allowed", False),
        "client_wants_replacements_back": front.get("wants_pieces_back", True),
        "customer_vehicle": front.get("vehicle_id", None),
    }
