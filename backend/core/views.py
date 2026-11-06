
import logging
import asyncio
import mimetypes

from django.http import HttpResponse
from django.utils.http import content_disposition_header
from vercel.blob import get_blob
from django.shortcuts import render
from django.db import IntegrityError
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.models import Membership

from .models import (
    ChatMessage,
    Conversation,
    Document,
    UserMemory,
)

from .serializers import (
    AskDocumentSerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    DocumentSerializer,
)
from django.core.exceptions import ValidationError

from .memory_service import (
    get_user_memories,
    save_user_memory,
    delete_user_memory,
)
from .agentic_workflow import run_agentic_workflow
from .document_ingestion import extract_document_text


logger = logging.getLogger(__name__)


class OrganizationDocumentListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_organization_membership(self, request, organization_id):
        return Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).first()

    def get(self, request, organization_id):
        membership = self.get_organization_membership(
            request, organization_id
        )

        if membership is None:
            return Response(
                {"detail": "Organization not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        documents = Document.objects.filter(
            organization_id=organization_id
        ).order_by("-created_at")

        serializer = DocumentSerializer(
            documents,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)

    def post(self, request, organization_id):
        membership = self.get_organization_membership(
            request, organization_id
        )

        if membership is None:
            return Response(
                {"detail": "Organization not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        uploaded_file = request.FILES.get("file")

        if uploaded_file is None:
            return Response(
                {
                    "file": (
                        "Upload a supported document using the 'file' "
                        "field: PDF, DOCX, PPTX, XLSX, CSV, TXT, "
                        "Markdown, or HTML."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DocumentSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        document = serializer.save(
            organization_id=organization_id,
            uploaded_by=request.user,
            status=Document.Status.PROCESSING,
        )

        try:
            extracted_text = extract_document_text(document.file)

            document.extracted_text = extracted_text
            document.status = Document.Status.COMPLETED
            document.save(
                update_fields=["extracted_text", "status"]
            )

        except Exception as exc:
            logger.exception(
                "Document processing failed for document ID %s",
                document.id,
            )

            document.status = Document.Status.FAILED
            document.save(update_fields=["status"])

            if isinstance(exc, ValueError):
                detail = str(exc)
            else:
                detail = (
                    "The document could not be processed. "
                    "Please upload a valid, readable file."
                )

            return Response(
                {
                    "detail": detail,
                    "document_id": document.id,
                    "status": document.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            DocumentSerializer(
                document,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationAskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organization_id):
        membership = Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).first()

        if membership is None:
            return Response(
                {"detail": "Organization not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AskDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]
        memory_context = get_user_memories(
            user=request.user,
            organization=organization_id,
            limit=20,
            )
        # Execute the LangGraph RAG workflow.
        try:
            result = run_agentic_workflow(
                organization_id=organization_id,
                question=question,
                memory_context=memory_context,
            )

            answer = result["answer"]
            passages = result["passages"]

        except Exception:
            logger.exception(
                "Agentic workflow failed for organization %s",
                organization_id,
            )

            return Response(
                {
                    "detail": (
                        "AI answer generation failed. "
                        "Please try again later."
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        sources = [
            {
                "document_id": item["document_id"],
                "title": item["title"],
                "chunk_index": item["chunk_index"],
                "relevance_score": item["relevance_score"],
                "retrieval_methods": item.get(
                    "retrieval_methods", []
                ),
                "excerpt": item["text"],
            }
            for item in passages
        ]

        return Response(
            {
                "question": question,
                "answer": answer,
                "sources": sources,
            },
            status=status.HTTP_200_OK,
        )


def home(request):
    return render(request, "index.html")


class OrganizationDocumentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, organization_id, document_id):
        membership = Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).first()

        if membership is None:
            return Response(
                {"detail": "Organization not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only owners and admins may delete documents.
        allowed_roles = [
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
        ]

        if membership.role not in allowed_roles:
            return Response(
                {
                    "detail": (
                        "Only organization owners and admins "
                        "can delete documents."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        document = Document.objects.filter(
            id=document_id,
            organization_id=organization_id,
        ).first()

        if document is None:
            return Response(
                {"detail": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        file_name = document.file.name if document.file else None
        file_storage = document.file.storage if document.file else None

        document.delete()

        if file_name and file_storage:
            try:
                file_storage.delete(file_name)
            except Exception:
                logger.exception(
                    "Could not delete stored file for document %s",
                    document_id,
                )

        return Response(
            {"detail": "Document deleted successfully."},
            status=status.HTTP_200_OK,
        )


class OrganizationConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        membership = Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).first()

        if membership is None:
            return Response(
                {"detail": "Organization not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        conversations = Conversation.objects.filter(
            organization_id=organization_id,
            user=request.user,
        ).order_by("-updated_at")

        serializer = ConversationSerializer(
            conversations,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request, organization_id):
        membership = Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).first()

        if membership is None:
            return Response(
                {"detail": "Organization not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = serializer.save(
            organization_id=organization_id,
            user=request.user,
        )

        return Response(
            ConversationSerializer(conversation).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_conversation(self, request, organization_id, conversation_id):
        membership = Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).first()

        if membership is None:
            return None

        return Conversation.objects.filter(
            id=conversation_id,
            organization_id=organization_id,
            user=request.user,
        ).first()

    def get(self, request, organization_id, conversation_id):
        conversation = self.get_conversation(
            request,
            organization_id,
            conversation_id,
        )

        if conversation is None:
            return Response(
                {"detail": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConversationDetailSerializer(conversation)
        return Response(serializer.data)

    def delete(self, request, organization_id, conversation_id):
        conversation = self.get_conversation(
            request,
            organization_id,
            conversation_id,
        )

        if conversation is None:
            return Response(
                {"detail": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        conversation.delete()

        return Response(
            {"detail": "Conversation deleted successfully."},
            status=status.HTTP_200_OK,
        )


class OrganizationConversationAskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, organization_id, conversation_id):
        # 1. Verify organization membership.
        membership = Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).first()

        if membership is None:
            return Response(
                {"detail": "Organization not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Verify conversation ownership.
        conversation = Conversation.objects.filter(
            id=conversation_id,
            organization_id=organization_id,
            user=request.user,
        ).first()

        if conversation is None:
            return Response(
                {"detail": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Validate the question.
        serializer = AskDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]

        # 4. Load previous conversation history.
        previous_messages = list(
            conversation.messages.order_by(
                "-created_at", "-id"
            )[:10]
        )
        previous_messages.reverse()

        chat_history = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in previous_messages
        ]
        memory_context = get_user_memories(
            user=request.user,
            organization=organization_id,
            limit=20,
            )
        # 5. Execute LangGraph with conversation history.
        try:
            result = run_agentic_workflow(
                organization_id=organization_id,
                question=question,
                chat_history=chat_history,
                memory_context=memory_context,
            )

            answer = result["answer"]
            passages = result["passages"]

        except Exception:
            logger.exception(
                "Agentic workflow failed for conversation %s",
                conversation_id,
            )

            return Response(
                {
                    "detail": (
                        "AI answer generation failed. "
                        "Please try again later."
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 6. Automatically title a new conversation.
        if (
            conversation.title == "New conversation"
            and not conversation.messages.exists()
        ):
            title = " ".join(question.split())

            if len(title) > 60:
                title = title[:57].rstrip() + "..."

            conversation.title = title
            conversation.save(update_fields=["title"])

        # 7. Save the question and answer.
        ChatMessage.objects.create(
            conversation=conversation,
            role=ChatMessage.Role.USER,
            content=question,
        )

        ChatMessage.objects.create(
            conversation=conversation,
            role=ChatMessage.Role.ASSISTANT,
            content=answer,
        )

        # 8. Update conversation activity.
        conversation.save(update_fields=["updated_at"])

        # 9. Prepare source information.
        sources = [
            {
                "document_id": item["document_id"],
                "title": item["title"],
                "chunk_index": item["chunk_index"],
                "relevance_score": item["relevance_score"],
                "retrieval_methods": item.get(
                    "retrieval_methods", []
                ),
                "excerpt": item["text"],
            }
            for item in passages
        ]

        return Response(
            {
                "conversation_id": conversation.id,
                "question": question,
                "answer": answer,
                "sources": sources,
            },
            status=status.HTTP_200_OK,
        )
class OrganizationMemoryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def check_membership(self, request, organization_id):
        return Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).exists()

    def get(self, request, organization_id):
        if not self.check_membership(request, organization_id):
            return Response(
                {"detail": "Organization not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        memories = UserMemory.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).order_by("-updated_at")

        data = [
            {
                "id": memory.id,
                "category": memory.category,
                "key": memory.key,
                "value": memory.value,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at,
            }
            for memory in memories
        ]

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, organization_id):
        if not self.check_membership(request, organization_id):
            return Response(
                {"detail": "Organization not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        key = request.data.get("key")
        value = request.data.get("value")
        category = request.data.get(
            "category",
            UserMemory.Category.PREFERENCE,
        )

        if not isinstance(key, str) or not isinstance(value, str):
            return Response(
                {"detail": "Both key and value must be strings."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            memory, created = save_user_memory(
                user=request.user,
                organization=organization_id,
                key=key,
                value=value,
                category=category,
            )
        except ValidationError as error:
            return Response(
                {"detail": error.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": memory.id,
                "category": memory.category,
                "key": memory.key,
                "value": memory.value,
                "created": created,
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class OrganizationMemoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_memory(self, request, organization_id, memory_id):
        membership_exists = Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).exists()

        if not membership_exists:
            return None

        return UserMemory.objects.filter(
            id=memory_id,
            user=request.user,
            organization_id=organization_id,
        ).first()

    def patch(self, request, organization_id, memory_id):
        memory = self.get_memory(
            request,
            organization_id,
            memory_id,
        )

        if memory is None:
            return Response(
                {"detail": "Memory not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        key = request.data.get("key", memory.key)
        value = request.data.get("value", memory.value)
        category = request.data.get(
            "category",
            memory.category,
        )

        # Validate data types.
        if not isinstance(key, str) or not isinstance(value, str):
            return Response(
                {"detail": "Key and value must be strings."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate empty values.
        if not key.strip() or not value.strip():
            return Response(
                {"detail": "Key and value cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate category.
        if category not in UserMemory.Category.values:
            return Response(
                {"detail": "Invalid memory category."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        memory.key = key.strip()
        memory.value = value.strip()
        memory.category = category

        try:
            memory.save(
                update_fields=[
                    "key",
                    "value",
                    "category",
                    "updated_at",
                ]
            )

        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "A memory with this key already exists "
                        "in this organization."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "id": memory.id,
                "category": memory.category,
                "key": memory.key,
                "value": memory.value,
                "updated_at": memory.updated_at,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, organization_id, memory_id):
        memory = self.get_memory(
            request,
            organization_id,
            memory_id,
        )

        if memory is None:
            return Response(
                {"detail": "Memory not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        memory.delete()

        return Response(
            {"detail": "Memory deleted successfully."},
            status=status.HTTP_200_OK,
        )

class OrganizationDocumentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id, document_id):
        # 1. Verify organization membership.
        membership = Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).first()

        if membership is None:
            return Response(
                {"detail": "Organization not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Find the requested document.
        document = Document.objects.filter(
            id=document_id,
            organization_id=organization_id,
        ).first()

        if document is None:
            return Response(
                {"detail": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Download and consume the Blob stream in one async operation.
        async def download_document():
            result = await get_blob(
                document.file.name,
                access="private",
            )

            if result is None or result.status_code != 200:
                raise FileNotFoundError("Document not found in Blob storage.")
            return result.body
            chunks = []

            async for chunk in result.stream:
                chunks.append(chunk)

            return b"".join(chunks)

        try:
            file_content = asyncio.run(download_document())

            # 4. Prepare the download response.
            filename = document.file.name.split("/")[-1]

            content_type = (
                mimetypes.guess_type(filename)[0]
                or "application/octet-stream"
            )

            response = HttpResponse(
                file_content,
                content_type=content_type,
            )

            response["Content-Disposition"] = content_disposition_header(
                True,
                filename,
            )
            response["X-Content-Type-Options"] = "nosniff"
            response["Cache-Control"] = "private, no-store"

            return response

        except FileNotFoundError:
            return Response(
                {"detail": "Document file not found in storage."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception:
            logger.exception(
                "Document download failed for document ID %s",
                document.id,
            )

            return Response(
                {"detail": "Unable to download this document."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
