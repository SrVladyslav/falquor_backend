from customers.views import WorkshopCustomersViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"customers", WorkshopCustomersViewSet, basename="customers")
urlpatterns = router.urls
