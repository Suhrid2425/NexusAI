from django.core.exceptions import ValidationError

from .models import UserMemory


def get_user_memories(user, organization, limit=20):
    """
    Retrieve memories belonging only to the given user
    and organization.
    """

    memories = UserMemory.objects.filter(
        user=user,
        organization=organization,
    ).order_by("-updated_at")[:limit]

    return [
        {
            "category": memory.category,
            "key": memory.key,
            "value": memory.value,
        }
        for memory in memories
    ]


def save_user_memory(
    user,
    organization,
    key,
    value,
    category=UserMemory.Category.PREFERENCE,
):
    """
    Create a memory or update the existing memory
    with the same key for this user and organization.
    """

    if not key or not key.strip():
        raise ValidationError("Memory key cannot be empty.")

    if not value or not value.strip():
        raise ValidationError("Memory value cannot be empty.")

    if category not in UserMemory.Category.values:
        raise ValidationError("Invalid memory category.")

    memory, created = UserMemory.objects.update_or_create(
        user=user,
        organization=organization,
        key=key.strip(),
        defaults={
            "value": value.strip(),
            "category": category,
        },
    )

    return memory, created


def delete_user_memory(user, organization, memory_id):
    """
    Delete only a memory owned by this user
    in this organization.
    """

    deleted_count, _ = UserMemory.objects.filter(
        id=memory_id,
        user=user,
        organization=organization,
    ).delete()

    return deleted_count > 0