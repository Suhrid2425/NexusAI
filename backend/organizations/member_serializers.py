
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Membership

User = get_user_model()


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[
            (Membership.Role.ADMIN, "Admin"),
            (Membership.Role.MEMBER, "Member"),
        ],
        default=Membership.Role.MEMBER,
    )

    def validate_email(self, value):
        users = User.objects.filter(email__iexact=value)

        if not users.exists():
            raise serializers.ValidationError(
                "No registered user found with this email."
            )

        if users.count() > 1:
            raise serializers.ValidationError(
                "Multiple accounts use this email. Contact support."
            )

        self.user_to_add = users.first()
        return value

    def validate(self, attrs):
        organization = self.context["organization"]
        user = self.user_to_add

        if Membership.objects.filter(
            user=user,
            organization=organization,
        ).exists():
            raise serializers.ValidationError(
                {"email": "This user is already a member."}
            )

        attrs["user"] = user
        return attrs

    def create(self, validated_data):
        organization = self.context["organization"]

        return Membership.objects.create(
            user=validated_data["user"],
            organization=organization,
            role=validated_data["role"],
        )


class MemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )
    email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = Membership
        fields = [
            "id",
            "username",
            "email",
            "organization",
            "role",
            "created_at",
        ]
        read_only_fields = fields


class UpdateMemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            (Membership.Role.ADMIN, "Admin"),
            (Membership.Role.MEMBER, "Member"),
        ]
    )
