from mechanic_workshop.views import WorkshopEntrancesViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"entrances", WorkshopEntrancesViewSet, basename="entrances")
urlpatterns = router.urls
