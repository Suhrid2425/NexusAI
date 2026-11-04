
from rest_framework.permissions import BasePermission

from .models import Membership


class CanManageMembers(BasePermission):
    """
    Only organization OWNER and ADMIN can manage members.
    """

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
        )

    def has_object_permission(self, request, view, organization):
        return Membership.objects.filter(
            user=request.user,
            organization=organization,
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            ],
        ).exists()
