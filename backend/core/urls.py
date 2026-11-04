from django.urls import path

from .views import (
    OrganizationAskView,
    OrganizationConversationAskView,
    OrganizationConversationDetailView,
    OrganizationConversationListCreateView,
    OrganizationDocumentDeleteView,
    OrganizationDocumentListCreateView,
    OrganizationMemoryListCreateView,
    OrganizationMemoryDetailView,
)

urlpatterns = [
    path(
        "organizations/<int:organization_id>/documents/",
        OrganizationDocumentListCreateView.as_view(),
        name="organization-documents",
    ),
    path(
        "organizations/<int:organization_id>/documents/<int:document_id>/",
        OrganizationDocumentDeleteView.as_view(),
        name="organization-document-delete",
    ),
    path(
        "organizations/<int:organization_id>/ask/",
        OrganizationAskView.as_view(),
        name="organization-ask",
    ),
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