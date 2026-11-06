
from pathlib import Path

from django.urls import reverse
from rest_framework import serializers

from .models import ChatMessage, Conversation, Document


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".csv",
    ".txt",
    ".md",
    ".html",
    ".htm",
}

# Keep below Vercel's 4.5 MB request-body limit.
MAX_FILE_SIZE = 4 * 1024 * 1024  # 4 MB


class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "organization",
            "uploaded_by",
            "title",
            "file",
            "download_url",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "uploaded_by",
            "status",
            "created_at",
        ]

    def get_download_url(self, obj):
        request = self.context.get("request")

        url = reverse(
            "organization-document-download",
            kwargs={
                "organization_id": obj.organization_id,
                "document_id": obj.id,
            },
        )

        if request:
            return request.build_absolute_uri(url)

        return url

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Document title cannot be empty."
            )

        return value

    def validate_file(self, value):
        extension = Path(value.name).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise serializers.ValidationError(
                f"Unsupported file format. Supported formats: {supported}"
            )

        if value.size == 0:
            raise serializers.ValidationError(
                "The uploaded file is empty."
            )

        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                "Maximum file size is 4 MB."
            )

        if extension == ".pdf":
            current_position = value.tell()
            header = value.read(5)
            value.seek(current_position)

            if header != b"%PDF-":
                raise serializers.ValidationError(
                    "The uploaded file does not appear to be a valid PDF."
                )

        return value


class AskDocumentSerializer(serializers.Serializer):
    question = serializers.CharField(
        max_length=2000,
        trim_whitespace=True,
        allow_blank=False,
    )

    def validate_question(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Question cannot be empty."
            )

        return value


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "created_at"]
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "organization",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Conversation title cannot be empty."
            )

        return value


class ConversationDetailSerializer(ConversationSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]
