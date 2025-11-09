from django.urls import path, include
from workspace_modules.views import WorkspaceViewSet
from rest_framework.routers import DefaultRouter
from workspace_modules.views import WorkspaceViewSet

router = DefaultRouter()
router.register(r"workspaces", WorkspaceViewSet, basename="workspaces")

urlpatterns = [
    path("", include(router.urls)),
    # path("workspaces/", WorkspaceViewSet.as_view()),
]
