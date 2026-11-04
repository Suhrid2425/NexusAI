
from django.db import transaction
from rest_framework import permissions, viewsets

from .models import Membership, Organization
from .serializers import OrganizationSerializer


class OrganizationRolePermission(permissions.BasePermission):
    """
    Owners and admins can update organizations.
    Only owners can delete organizations.
    Organization members can view their organizations.
    """

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        # The queryset already limits access to the user's organizations.
        if request.method in permissions.SAFE_METHODS:
            return True

        role = Membership.objects.filter(
            user=request.user,
            organization=obj,
        ).values_list("role", flat=True).first()

        if request.method in ("PUT", "PATCH"):
            return role in (
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            )

        if request.method == "DELETE":
            return role == Membership.Role.OWNER

        return False


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [OrganizationRolePermission]

    def get_queryset(self):
        return Organization.objects.filter(
            memberships__user=self.request.user
        ).distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        organization = serializer.save()

        Membership.objects.create(
            user=self.request.user,
            organization=organization,
            role=Membership.Role.OWNER,
        )
