from django.urls import path
from sidebar_nav.views import SidebarNavView

urlpatterns = [
    path(
        "workspaces/<str:workspace_id>/manifest",
        SidebarNavView.as_view(),
        name="workspace-manifest",
    ),
]
