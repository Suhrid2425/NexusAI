
import math


def recall_at_k(retrieved, relevant, k=5):
    """Fraction of relevant chunks found in the top K results."""
    relevant = set(relevant)

    if not relevant:
        return 0.0

    retrieved_ids = {
        (item["document_id"], item["chunk_index"])
        for item in retrieved[:k]
    }

    return len(retrieved_ids & relevant) / len(relevant)


def precision_at_k(retrieved, relevant, k=5):
    """Fraction of the top K retrieved chunks that are relevant."""
    relevant = set(relevant)

    if k <= 0:
        return 0.0

    retrieved_ids = [
        (item["document_id"], item["chunk_index"])
        for item in retrieved[:k]
    ]

    if not retrieved_ids:
        return 0.0

    hits = sum(item in relevant for item in retrieved_ids)
    return hits / k


def reciprocal_rank(retrieved, relevant):
    """Reciprocal rank of the first relevant result."""
    relevant = set(relevant)

    for rank, item in enumerate(retrieved, start=1):
        chunk_id = (item["document_id"], item["chunk_index"])

        if chunk_id in relevant:
            return 1.0 / rank

    return 0.0


def ndcg_at_k(retrieved, relevant, k=5):
    """Normalized Discounted Cumulative Gain."""
    relevant = set(relevant)

    if not relevant or k <= 0:
        return 0.0

    dcg = 0.0

    for rank, item in enumerate(retrieved[:k], start=1):
        chunk_id = (item["document_id"], item["chunk_index"])

        if chunk_id in relevant:
            dcg += 1.0 / math.log2(rank + 1)

    ideal_hits = min(len(relevant), k)

    idcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(1, ideal_hits + 1)
    )

    return dcg / idcg if idcg else 0.0


def evaluate_retrieval(retrieved, relevant, k=5):
    """Calculate all retrieval metrics for one question."""

    return {
        "recall_at_k": recall_at_k(retrieved, relevant, k),
        "precision_at_k": precision_at_k(retrieved, relevant, k),
        "mrr": reciprocal_rank(retrieved, relevant),
        "ndcg_at_k": ndcg_at_k(retrieved, relevant, k),
    }
