
from django.urls import path

from .views import (
    OrganizationAskView,
    OrganizationConversationAskView,
    OrganizationConversationDetailView,
    OrganizationConversationListCreateView,
    OrganizationDocumentDeleteView,
    OrganizationDocumentDownloadView,
    OrganizationDocumentListCreateView,
    OrganizationMemoryListCreateView,
    OrganizationMemoryDetailView,
)

urlpatterns = [
    # Document endpoints
    path(
        "organizations/<int:organization_id>/documents/",
        OrganizationDocumentListCreateView.as_view(),
        name="organization-documents",
    ),
    path(
        "organizations/<int:organization_id>/documents/<int:document_id>/download/",
        OrganizationDocumentDownloadView.as_view(),
        name="organization-document-download",
    ),
    path(
        "organizations/<int:organization_id>/documents/<int:document_id>/",
        OrganizationDocumentDeleteView.as_view(),
        name="organization-document-delete",
    ),

    # Organization AI endpoints
    path(
        "organizations/<int:organization_id>/ask/",
        OrganizationAskView.as_view(),
        name="organization-ask",
    ),

    # Conversation endpoints
    path(
        "organizations/<int:organization_id>/conversations/",
        OrganizationConversationListCreateView.as_view(),
        name="organization-conversations",
    ),
    path(
        "organizations/<int:organization_id>/conversations/<int:conversation_id>/",
        OrganizationConversationDetailView.as_view(),
        name="organization-conversation-detail",
    ),
    path(
        "organizations/<int:organization_id>/conversations/<int:conversation_id>/ask/",
        OrganizationConversationAskView.as_view(),
        name="organization-conversation-ask",
    ),

    # Memory endpoints
    path(
        "organizations/<int:organization_id>/memories/",
        OrganizationMemoryListCreateView.as_view(),
        name="organization-memories",
    ),
    path(
        "organizations/<int:organization_id>/memories/<int:memory_id>/",
        OrganizationMemoryDetailView.as_view(),
        name="organization-memory-detail",
    ),
]
