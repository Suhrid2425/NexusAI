
import hashlib
import os
from functools import lru_cache

import faiss
import numpy as np
import voyageai

from .models import Document
from .rag import split_into_chunks


MODEL_NAME = os.getenv(
    "VOYAGE_EMBEDDING_MODEL",
    "voyage-4-lite",
)

EMBEDDING_BATCH_SIZE = 64

# Cache the API client rather than loading a local ML model.
@lru_cache(maxsize=1)
def _get_embedding_client():
    """Create and reuse the Voyage API client."""

    api_key = os.getenv("VOYAGE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "VOYAGE_API_KEY is missing from environment variables."
        )

    return voyageai.Client(
        api_key=api_key,
        max_retries=2,
        timeout=60,
    )


def _generate_embeddings(texts, input_type):
    """
    Generate embeddings using the hosted Voyage API.

    Processes texts in batches to avoid sending excessively
    large requests.
    """

    if not texts:
        return np.empty((0, 1024), dtype=np.float32)

    client = _get_embedding_client()
    all_embeddings = []

    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start:start + EMBEDDING_BATCH_SIZE]

        result = client.embed(
            texts=batch,
            model=MODEL_NAME,
            input_type=input_type,
        )

        all_embeddings.extend(result.embeddings)

    vectors = np.asarray(
        all_embeddings,
        dtype=np.float32,
    )

    # Normalize vectors so inner product represents cosine similarity.
    faiss.normalize_L2(vectors)

    return np.ascontiguousarray(vectors, dtype=np.float32)


# In-memory cache:
# organization_id -> document fingerprint and indexed passages.
_embedding_cache = {}


def _load_passages(organization_id):
    """Load completed documents and create searchable chunks."""

    documents = Document.objects.filter(
        organization_id=organization_id,
        status=Document.Status.COMPLETED,
    ).exclude(
        extracted_text=""
    ).order_by("id")

    passages = []
    fingerprint_parts = []

    for document in documents:
        text = document.extracted_text or ""

        text_hash = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

        fingerprint_parts.append(
            (document.id, text_hash)
        )

        chunks = split_into_chunks(text)

        for chunk_index, chunk in enumerate(chunks):
            passages.append({
                "document_id": document.id,
                "title": document.title,
                "chunk_index": chunk_index,
                "text": chunk,
            })

    fingerprint = tuple(fingerprint_parts)

    return passages, fingerprint


def _get_index(organization_id):
    """Reuse an existing index unless document content changes."""

    passages, fingerprint = _load_passages(organization_id)

    cached = _embedding_cache.get(organization_id)

    if cached and cached["fingerprint"] == fingerprint:
        # Refresh passage metadata without rebuilding the FAISS index.
        cached["passages"] = passages
        return cached

    if not passages:
        _embedding_cache.pop(organization_id, None)
        return None

    # Generate document embeddings through MongoDB's hosted API.
    vectors = _generate_embeddings(
        [passage["text"] for passage in passages],
        input_type="document",
    )

    # Inner product on normalized vectors gives cosine similarity.
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    cached = {
        "fingerprint": fingerprint,
        "passages": passages,
        "index": index,
    }

    _embedding_cache[organization_id] = cached

    return cached


def retrieve_semantic_chunks(
    organization_id,
    question,
    top_k=4,
    min_score=0.0,
):
    """
    Retrieve document chunks using semantic similarity.

    Args:
        organization_id: Organization whose documents are searched.
        question: User's question.
        top_k: Maximum number of chunks to return.
        min_score: Minimum cosine similarity score to keep.

    Returns:
        A list of relevant passages with similarity scores.
    """

    if (
        not isinstance(question, str)
        or not question.strip()
        or top_k < 1
        or not 0.0 <= min_score <= 1.0
    ):
        return []

    cached = _get_index(organization_id)

    if cached is None:
        return []

    # Generate the question embedding through the hosted API.
    question_vector = _generate_embeddings(
        [question.strip()],
        input_type="query",
    )

    # Search for the nearest passages.
    k = min(top_k, len(cached["passages"]))

    scores, indices = cached["index"].search(
        question_vector,
        k,
    )

    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue

        score = float(score)

        if score < min_score:
            continue

        result = cached["passages"][int(idx)].copy()
        result["relevance_score"] = round(score, 4)

        results.append(result)

    return results
