
from .bm25_rag import retrieve_bm25_chunks
from .semantic_rag import retrieve_semantic_chunks


def retrieve_hybrid_chunks(
    organization_id,
    question,
    top_k=4,
    candidate_k=10,
):
    """
    Combine BM25 and semantic retrieval using
    Reciprocal Rank Fusion (RRF).

    Original retrieval scores are preserved separately.
    """

    if (
        not isinstance(question, str)
        or not question.strip()
        or top_k < 1
        or candidate_k < 1
    ):
        return []

    candidate_k = max(top_k, candidate_k)

    # 1. Sparse retrieval using BM25
    bm25_results = retrieve_bm25_chunks(
        organization_id=organization_id,
        question=question,
        top_k=candidate_k,
    )

    # 2. Dense retrieval using semantic embeddings
    semantic_results = retrieve_semantic_chunks(
        organization_id=organization_id,
        question=question,
        top_k=candidate_k,
        min_score=0.0,
    )

    combined = {}

    def add_results(passages, method):
        for rank, passage in enumerate(passages, start=1):

            key = (
                passage["document_id"],
                passage["chunk_index"],
            )

            if key not in combined:
                combined[key] = {
                    **passage,
                    "hybrid_score": 0.0,
                    "retrieval_methods": [],
                    "bm25_score": None,
                    "semantic_score": None,
                }

            item = combined[key]

            # Reciprocal Rank Fusion
            item["hybrid_score"] += 1.0 / (60 + rank)

            if method not in item["retrieval_methods"]:
                item["retrieval_methods"].append(method)

            score = passage.get("relevance_score")

            if method == "bm25" and score is not None:
                item["bm25_score"] = score

            elif method == "semantic" and score is not None:
                item["semantic_score"] = score

            # Preserve metadata from either retriever.
            for field, value in passage.items():
                if item.get(field) is None:
                    item[field] = value

    # 3. Fuse both retrieval rankings
    add_results(bm25_results, "bm25")
    add_results(semantic_results, "semantic")

    # 4. Rank by fused score
    ranked_results = sorted(
        combined.values(),
        key=lambda item: item["hybrid_score"],
        reverse=True,
    )

    # 5. Return top-K results
    results = []

    for passage in ranked_results[:top_k]:
        result = passage.copy()

        # RRF score is not a probability.
        result["relevance_score"] = round(
            result["hybrid_score"],
            6,
        )

        results.append(result)

    return results
