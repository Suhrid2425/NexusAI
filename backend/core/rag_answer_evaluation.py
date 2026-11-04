import json
import os

from groq import Groq


def evaluate_answer(question, answer, passages):
    """
    Evaluate a RAG-generated answer for:
    1. Faithfulness
    2. Answer relevance
    3. Answer completeness
    4. Citation correctness
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if not answer or not answer.strip():
        raise ValueError("Answer cannot be empty.")

    if not isinstance(passages, list):
        raise ValueError("Passages must be a list.")

    if not passages:
        raise ValueError("Passages cannot be empty.")

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing.")

    client = Groq(
        api_key=api_key,
        timeout=30.0,
        max_retries=1,
    )

    context = "\n\n".join(
        (
            f"[Source {index}]\n"
            f"Document: {passage.get('title', 'Untitled')}\n"
            f"{passage.get('text', '')}"
        )
        for index, passage in enumerate(passages, start=1)
    )

    evaluation_prompt = f"""
You are an independent evaluator for an enterprise RAG system.

Evaluate the answer using ONLY the question and supplied sources.

QUESTION:
{question}

SOURCES:
{context}

GENERATED ANSWER:
{answer}

Score each metric from 0 to 5.

1. faithfulness:
Are the factual claims supported by the sources?

2. answer_relevance:
Does the answer directly address the question?

3. completeness:
Does the answer include the important information needed?

4. citation_correctness:
Are citations valid and do they support the associated claims?

Return ONLY valid JSON in this exact structure:

{{
    "faithfulness": 0,
    "answer_relevance": 0,
    "completeness": 0,
    "citation_correctness": 0,
    "overall_score": 0,
    "reasoning": "Brief explanation",
    "issues": []
}}

Use integer scores from 0 to 5.
Do not reward unsupported claims.
"""

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict RAG evaluation system. "
                    "Return only valid JSON."
                ),
            },
            {
                "role": "user",
                "content": evaluation_prompt,
            },
        ],
        temperature=0,
        max_completion_tokens=1000,
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("The evaluator returned an empty response.")

    result = json.loads(content)

    score_fields = [
        "faithfulness",
        "answer_relevance",
        "completeness",
        "citation_correctness",
        "overall_score",
    ]

    for field in score_fields:
        score = result.get(field)

        if not isinstance(score, int) or not 0 <= score <= 5:
            raise ValueError(
                f"Invalid evaluation score for {field}: {score}"
            )

    return result