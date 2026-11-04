import re

from rank_bm25 import BM25Okapi

from .models import Document
from .rag import split_into_chunks


def tokenize_text(text):
    """
    Convert text into lowercase word tokens.
    Supports English words, numbers and technical terms.
    """
    return re.findall(r"\b[a-zA-Z0-9_+#.-]+\b", text.lower())


def retrieve_bm25_chunks(
    organization_id,
    question,
    top_k=10,
):
    """
    Retrieve relevant document chunks using BM25.

    Searches only completed documents belonging to the
    requested organization.
    """

    if (
        not isinstance(question, str)
        or not question.strip()
        or top_k < 1
    ):
        return []

    documents = Document.objects.filter(
        organization_id=organization_id,
        status=Document.Status.COMPLETED,
    ).exclude(
        extracted_text=""
    ).order_by("id")

    passages = []

    for document in documents:
        chunks = split_into_chunks(
            document.extracted_text or ""
        )

        for chunk_index, chunk in enumerate(chunks):
            passages.append({
                "document_id": document.id,
                "title": document.title,
                "chunk_index": chunk_index,
                "text": chunk,
            })

    if not passages:
        return []

    tokenized_passages = [
        tokenize_text(passage["text"])
        for passage in passages
    ]

    query_tokens = tokenize_text(question)

    if not query_tokens:
        return []

    bm25 = BM25Okapi(tokenized_passages)

    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )

    results = []

    for index in ranked_indices:
        score = float(scores[index])

        # Ignore chunks with no positive BM25 relevance.
        if score <= 0:
            continue

        results.append({
            **passages[index],
            "relevance_score": round(score, 4),
        })

        if len(results) >= top_k:
            break

    return results