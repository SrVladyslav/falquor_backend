from mechanic_workshop.models.warehouses import Warehouse, WarehouseInventory
from uuid import UUID


def get_warehouse_tags(warehouse_uuid: UUID) -> list[str]:
    """Returns a list of tags for the given warehouse."""
    data = (
        WarehouseInventory.objects.filter(
            warehouse__uuid=warehouse_uuid, group_tag__isnull=False
        )
        .values_list("group_tag", flat=True)
        .distinct()
        .order_by("group_tag")
    )
    return list(data)
