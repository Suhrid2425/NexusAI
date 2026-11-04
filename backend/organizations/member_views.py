
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Organization, Membership
from .member_serializers import (
    AddMemberSerializer,
    MemberSerializer,
    UpdateMemberRoleSerializer,
)


class OrganizationMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def get_organization(self, request, organization_id):
        return get_object_or_404(
            Organization.objects.filter(
                memberships__user=request.user
            ).distinct(),
            id=organization_id,
        )

    def get(self, request, organization_id):
        organization = self.get_organization(
            request, organization_id
        )

        memberships = Membership.objects.filter(
            organization=organization
        ).select_related("user", "organization").order_by("id")

        serializer = MemberSerializer(memberships, many=True)

        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, organization_id):
        organization = self.get_organization(
            request, organization_id
        )

        current_membership = get_object_or_404(
            Membership.objects.select_for_update(),
            user=request.user,
            organization=organization,
        )

        if current_membership.role not in (
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
        ):
            return Response(
                {"detail": "You do not have permission to add members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AddMemberSerializer(
            data=request.data,
            context={"organization": organization},
        )
        serializer.is_valid(raise_exception=True)

        requested_role = serializer.validated_data["role"]

        # Only the OWNER can add another ADMIN.
        if (
            requested_role == Membership.Role.ADMIN
            and current_membership.role != Membership.Role.OWNER
        ):
            return Response(
                {"detail": "Only the organization owner can add admins."},
                status=status.HTTP_403_FORBIDDEN,
            )

        membership = serializer.save()

        return Response(
            MemberSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationMemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_membership(self, request, organization_id, member_id):
        organization = get_object_or_404(
            Organization.objects.filter(
                memberships__user=request.user
            ).distinct(),
            id=organization_id,
        )

        current_membership = get_object_or_404(
            Membership,
            user=request.user,
            organization=organization,
        )

        target_membership = get_object_or_404(
            Membership.objects.select_related("user"),
            id=member_id,
            organization=organization,
        )

        return current_membership, target_membership

    def check_management_permission(
        self, current_membership, target_membership
    ):
        if current_membership.role not in (
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
        ):
            return False

        # An OWNER cannot be modified or removed through this endpoint.
        if target_membership.role == Membership.Role.OWNER:
            return False

        # ADMINs cannot manage other ADMINs.
        if (
            current_membership.role == Membership.Role.ADMIN
            and target_membership.role == Membership.Role.ADMIN
        ):
            return False

        return True

    @transaction.atomic
    def patch(self, request, organization_id, member_id):
        current_membership, target_membership = self.get_membership(
            request, organization_id, member_id
        )

        if not self.check_management_permission(
            current_membership, target_membership
        ):
            return Response(
                {"detail": "You do not have permission to change this member."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = UpdateMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_role = serializer.validated_data["role"]

        # Only OWNER can promote someone to ADMIN.
        if (
            new_role == Membership.Role.ADMIN
            and current_membership.role != Membership.Role.OWNER
        ):
            return Response(
                {"detail": "Only the organization owner can assign the ADMIN role."},
                status=status.HTTP_403_FORBIDDEN,
            )

        target_membership.role = new_role
        target_membership.save(update_fields=["role"])

        return Response(MemberSerializer(target_membership).data)

    @transaction.atomic
    def delete(self, request, organization_id, member_id):
        current_membership, target_membership = self.get_membership(
            request, organization_id, member_id
        )

        if not self.check_management_permission(
            current_membership, target_membership
        ):
            return Response(
                {"detail": "You do not have permission to remove this member."},
                status=status.HTTP_403_FORBIDDEN,
            )

        target_membership.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
