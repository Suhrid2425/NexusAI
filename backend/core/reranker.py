
import os
from functools import lru_cache

import voyageai


MODEL_NAME = os.getenv(
    "VOYAGE_RERANK_MODEL",
    "rerank-3-lite",
)


@lru_cache(maxsize=1)
def get_reranker():
    """
    Create and reuse the hosted Voyage API client.
    """

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


def rerank_chunks(question, passages, top_k=4):
    """
    Rerank retrieved passages using Voyage's hosted reranking API.

    The API evaluates the question and each passage together.
    """

    if (
        not isinstance(question, str)
        or not question.strip()
        or not passages
        or top_k < 1
    ):
        return []

    client = get_reranker()

    documents = [
        passage["text"]
        for passage in passages
    ]

    response = client.rerank(
        query=question.strip(),
        documents=documents,
        model=MODEL_NAME,
        top_k=min(top_k, len(documents)),
    )

    ranked_passages = []

    for item in response.results:
        # Map the API result back to the original passage.
        result = passages[item.index].copy()

        result["reranker_score"] = float(
            item.relevance_score
        )

        ranked_passages.append(result)

    return ranked_passages
