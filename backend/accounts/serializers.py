from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.text import slugify

from rest_framework import serializers

from organizations.models import Organization, Membership


User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    password_confirm = serializers.CharField(
        write_only=True,
    )

    organization_name = serializers.CharField(
        write_only=True,
        max_length=255,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "organization_name",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {
                    "password_confirm": "Passwords do not match."
                }
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        organization_name = validated_data.pop("organization_name")
        validated_data.pop("password_confirm")

        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data,
        )

        slug = slugify(organization_name)

        organization = Organization.objects.create(
            name=organization_name,
            slug=slug,
        )

        Membership.objects.create(
            user=user,
            organization=organization,
            role=Membership.Role.OWNER,
        )

        return user
    