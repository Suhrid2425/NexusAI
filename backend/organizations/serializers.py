
from django.utils.text import slugify
from rest_framework import serializers

from .models import Organization, Membership


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        name = validated_data["name"]
        base_slug = slugify(name)

        if not base_slug:
            raise serializers.ValidationError({
                "name": "Please provide a valid organization name."
            })

        slug = base_slug
        counter = 2

        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        validated_data["slug"] = slug

        return Organization.objects.create(**validated_data)


class MembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "username",
            "organization",
            "role",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]
