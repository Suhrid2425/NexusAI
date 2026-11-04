
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import OrganizationViewSet
from .member_views import (
    OrganizationMemberView,
    OrganizationMemberDetailView,
)

router = DefaultRouter()

router.register(
    r"organizations",
    OrganizationViewSet,
    basename="organization",
)

urlpatterns = [
    *router.urls,

    path(
        "organizations/<int:organization_id>/members/",
        OrganizationMemberView.as_view(),
        name="organization-members",
    ),

    path(
        "organizations/<int:organization_id>/members/<int:member_id>/",
        OrganizationMemberDetailView.as_view(),
        name="organization-member-detail",
    ),
]
