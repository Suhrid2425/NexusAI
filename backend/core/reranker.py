
from functools import lru_cache

from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def get_reranker():
    """
    Load the cross-encoder once and reuse it.
    """
    return CrossEncoder(MODEL_NAME)


def rerank_chunks(question, passages, top_k=4):
    """
    Rerank retrieved passages using a cross-encoder.

    The model evaluates the question and each passage together.
    """

    if (
        not isinstance(question, str)
        or not question.strip()
        or not passages
        or top_k < 1
    ):
        return []

    model = get_reranker()

    pairs = [
        (question, passage["text"])
        for passage in passages
    ]

    scores = model.predict(pairs)

    ranked_passages = []

    for passage, score in zip(passages, scores):
        result = passage.copy()

        result["reranker_score"] = float(score)

        ranked_passages.append(result)

    ranked_passages.sort(
        key=lambda item: item["reranker_score"],
        reverse=True,
    )

    return ranked_passages[:top_k]
