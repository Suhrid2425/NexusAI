
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from .models import Organization, Membership

User = get_user_model()


class OrganizationMemberAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Create organization
        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
        )

        self.other_organization = Organization.objects.create(
            name="Other Organization",
            slug="other-organization",
        )

        # Create users
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="TestPassword123!",
        )

        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="TestPassword123!",
        )

        self.member = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="TestPassword123!",
        )

        self.candidate = User.objects.create_user(
            username="candidate",
            email="candidate@example.com",
            password="TestPassword123!",
        )

        self.outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="TestPassword123!",
        )

        # Create memberships
        self.owner_membership = Membership.objects.create(
            user=self.owner,
            organization=self.organization,
            role=Membership.Role.OWNER,
        )

        self.admin_membership = Membership.objects.create(
            user=self.admin,
            organization=self.organization,
            role=Membership.Role.ADMIN,
        )

        self.member_membership = Membership.objects.create(
            user=self.member,
            organization=self.organization,
            role=Membership.Role.MEMBER,
        )

        self.outsider_membership = Membership.objects.create(
            user=self.outsider,
            organization=self.other_organization,
            role=Membership.Role.OWNER,
        )

        self.members_url = (
            f"/api/organizations/{self.organization.id}/members/"
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    # -------------------------------------------------
    # GET MEMBERS
    # -------------------------------------------------

    def test_owner_can_list_members(self):
        self.authenticate(self.owner)

        response = self.client.get(self.members_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_member_can_list_members(self):
        self.authenticate(self.member)

        response = self.client.get(self.members_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_outsider_cannot_list_members(self):
        self.authenticate(self.outsider)

        response = self.client.get(self.members_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------
    # ADD MEMBERS
    # -------------------------------------------------

    def test_owner_can_add_member(self):
        self.authenticate(self.owner)

        response = self.client.post(
            self.members_url,
            {
                "email": "candidate@example.com",
                "role": Membership.Role.MEMBER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(
            Membership.objects.filter(
                user=self.candidate,
                organization=self.organization,
                role=Membership.Role.MEMBER,
            ).exists()
        )

    def test_owner_can_add_admin(self):
        self.authenticate(self.owner)

        response = self.client.post(
            self.members_url,
            {
                "email": "candidate@example.com",
                "role": Membership.Role.ADMIN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_can_add_member(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.members_url,
            {
                "email": "candidate@example.com",
                "role": Membership.Role.MEMBER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_cannot_add_admin(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.members_url,
            {
                "email": "candidate@example.com",
                "role": Membership.Role.ADMIN,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_member_cannot_add_members(self):
        self.authenticate(self.member)

        response = self.client.post(
            self.members_url,
            {
                "email": "candidate@example.com",
                "role": Membership.Role.MEMBER,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_duplicate_member_cannot_be_added(self):
        self.authenticate(self.owner)

        response = self.client.post(
            self.members_url,
            {
                "email": "admin@example.com",
                "role": Membership.Role.MEMBER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------
    # UPDATE MEMBER ROLE
    # -------------------------------------------------

    def test_owner_can_promote_member_to_admin(self):
        self.authenticate(self.owner)

        response = self.client.patch(
            f"{self.members_url}{self.member_membership.id}/",
            {"role": Membership.Role.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.member_membership.refresh_from_db()

        self.assertEqual(
            self.member_membership.role,
            Membership.Role.ADMIN,
        )

    def test_admin_cannot_promote_member_to_admin(self):
        self.authenticate(self.admin)

        response = self.client.patch(
            f"{self.members_url}{self.member_membership.id}/",
            {"role": Membership.Role.ADMIN},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_owner_cannot_demote_owner(self):
        self.authenticate(self.owner)

        response = self.client.patch(
            f"{self.members_url}{self.owner_membership.id}/",
            {"role": Membership.Role.MEMBER},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    # -------------------------------------------------
    # DELETE MEMBERS
    # -------------------------------------------------

    def test_owner_can_remove_member(self):
        self.authenticate(self.owner)

        response = self.client.delete(
            f"{self.members_url}{self.member_membership.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Membership.objects.filter(
                id=self.member_membership.id
            ).exists()
        )

    def test_admin_can_remove_member(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            f"{self.members_url}{self.member_membership.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_member_cannot_remove_another_member(self):
        self.authenticate(self.member)

        response = self.client.delete(
            f"{self.members_url}{self.admin_membership.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_owner_cannot_remove_owner(self):
        self.authenticate(self.owner)

        response = self.client.delete(
            f"{self.members_url}{self.owner_membership.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    # -------------------------------------------------
    # ORGANIZATION ISOLATION
    # -------------------------------------------------

    def test_cannot_access_membership_from_another_organization(self):
        self.authenticate(self.owner)

        response = self.client.delete(
            f"/api/organizations/{self.organization.id}/members/"
            f"{self.outsider_membership.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(
            Membership.objects.filter(
                id=self.outsider_membership.id
            ).exists()
        )
