from django.contrib import admin
from mechanic_workshop.models.base import MechanicWorkshop
from mechanic_workshop.models.service import LoanerCarHistory, LoanerCar
from mechanic_workshop.models.vacations import WorkerVacationInformation, LeaveDay
from mechanic_workshop.models.appointments import Appointment
from mechanic_workshop.models.warehouses import (
    Warehouse,
    WarehouseInventory,
    WarehouseItem,
)
from mechanic_workshop.models.workorders import (
    WorkOrder,
    WorkOrderDamageSketch,
    ReplacementPart,
    WorkOrderAssignment,
    Discount,
)
from mechanic_workshop.models.vehicles import CustomerVehicle

# Base
admin.site.register(MechanicWorkshop)
# Service
admin.site.register(LoanerCarHistory)
admin.site.register(LoanerCar)
# Vacations
admin.site.register(WorkerVacationInformation)
admin.site.register(LeaveDay)
# Appointments
admin.site.register(Appointment)
# Warehouses
admin.site.register(Warehouse)
admin.site.register(WarehouseInventory)
admin.site.register(WarehouseItem)
# Workorders
admin.site.register(WorkOrder)
admin.site.register(WorkOrderAssignment)
admin.site.register(Discount)
admin.site.register(ReplacementPart)
admin.site.register(WorkOrderDamageSketch)
# Customer Vehicles
admin.site.register(CustomerVehicle)
