
import hashlib
from functools import lru_cache

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .models import Document
from .rag import split_into_chunks


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Cache the model after its first use.
# Importing this module will no longer load the model immediately.
@lru_cache(maxsize=1)
def _get_embedding_model():
    """Load the embedding model only when semantic retrieval needs it."""
    return SentenceTransformer(MODEL_NAME)


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

        # Detect changes to document content.
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

    # Load the model only when embeddings are actually required.
    model = _get_embedding_model()

    vectors = model.encode(
        [passage["text"] for passage in passages],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    vectors = np.ascontiguousarray(
        vectors,
        dtype=np.float32,
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

    # The model is loaded here only if it was not already loaded
    # while building the document index.
    model = _get_embedding_model()

    question_vector = model.encode(
        [question.strip()],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    question_vector = np.ascontiguousarray(
        question_vector,
        dtype=np.float32,
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

        # Exclude passages below the requested threshold.
        if score < min_score:
            continue

        result = cached["passages"][int(idx)].copy()
        result["relevance_score"] = round(score, 4)

        results.append(result)

    return results
