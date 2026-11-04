
from statistics import mean

from .bm25_rag import retrieve_bm25_chunks
from .semantic_rag import retrieve_semantic_chunks
from .hybrid_rag import retrieve_hybrid_chunks
from .reranker import rerank_chunks

from .rag_evaluation import evaluate_retrieval
from .llm import generate_answer
from .rag_answer_evaluation import evaluate_answer


BENCHMARK_QUESTIONS = [
    {
        "question": "What are the important easy array questions for technical placements?",
        "relevant_chunks": [(5, 0)],
    },
    {
        "question": "Which medium-level array problems should I practice?",
        "relevant_chunks": [(5, 1)],
    },
    {
        "question": "What are the hard array problems for DSA interviews?",
        "relevant_chunks": [(5, 2)],
    },
    {
        "question": "Which searching algorithms and problems should I prepare?",
        "relevant_chunks": [(5, 3), (5, 4), (5, 5)],
    },
    {
        "question": "Which recursion problems are important for placements?",
        "relevant_chunks": [(5, 6), (5, 7), (5, 8)],
    },
    {
        "question": "What are the important string problems for coding interviews?",
        "relevant_chunks": [(5, 9), (5, 10), (5, 11)],
    },
    {
        "question": "How many annual and sick leave days do employees receive?",
        "relevant_chunks": [(6, 0)],
    },
    {
        "question": "What is the company's total revenue and net profit for FY 2025?",
        "relevant_chunks": [(7, 0)],
    },
    {
        "question": "How do clients authenticate API requests and when do access tokens expire?",
        "relevant_chunks": [(8, 0)],
    },
    {
        "question": "How was the document search research experiment evaluated?",
        "relevant_chunks": [(9, 0)],
    },
]


def run_rag_benchmark(organization_id=1, k=5):

    retrieval_results = {
        "BM25": [],
        "Semantic": [],
        "Hybrid": [],
        "Hybrid + Reranker": [],
    }

    answer_results = []
    failed_answers = []

    for index, benchmark in enumerate(BENCHMARK_QUESTIONS, start=1):

        question = benchmark["question"]
        relevant = benchmark["relevant_chunks"]

        print("\n" + "=" * 65)
        print(f"QUESTION {index}/{len(BENCHMARK_QUESTIONS)}")
        print(question)
        print("=" * 65)

        # 1. BM25 retrieval
        bm25_results = retrieve_bm25_chunks(
            organization_id=organization_id,
            question=question,
            top_k=10,
        )

        # 2. Semantic retrieval
        semantic_results = retrieve_semantic_chunks(
            organization_id=organization_id,
            question=question,
            top_k=10,
            min_score=0.0,
        )

        # 3. Hybrid retrieval
        hybrid_results = retrieve_hybrid_chunks(
            organization_id=organization_id,
            question=question,
            top_k=10,
            candidate_k=20,
        )

        # 4. Hybrid + Reranker
        reranked_results = rerank_chunks(
            question=question,
            passages=hybrid_results,
            top_k=10,
        )

        retrieval_methods = {
            "BM25": bm25_results,
            "Semantic": semantic_results,
            "Hybrid": hybrid_results,
            "Hybrid + Reranker": reranked_results,
        }

        # Evaluate retrieval quality
        for method, retrieved in retrieval_methods.items():

            metrics = evaluate_retrieval(
                retrieved=retrieved,
                relevant=relevant,
                k=k,
            )

            retrieval_results[method].append(metrics)

        # 5. Generate answer using top 4 reranked passages
        answer_passages = reranked_results[:4]

        try:

            if not answer_passages:
                raise ValueError("No passages available for answer generation.")

            answer = generate_answer(
                question=question,
                passages=answer_passages,
            )

            print("\nGENERATED ANSWER:")
            print(answer)

            # 6. Evaluate answer quality
            answer_metrics = evaluate_answer(
                question=question,
                answer=answer,
                passages=answer_passages,
            )

            answer_results.append(answer_metrics)

            print("\nANSWER QUALITY:")
            print(answer_metrics)

        except Exception as error:

            failed_answers.append({
                "question": question,
                "error": str(error),
            })

            print(f"\nANSWER EVALUATION FAILED: {error}")

    # -------------------------------------------------
    # FINAL RETRIEVAL BENCHMARK
    # -------------------------------------------------

    print("\n" + "=" * 65)
    print(f"RETRIEVAL BENCHMARK SUMMARY — K={k}")
    print("=" * 65)

    for method, scores in retrieval_results.items():

        print(f"\n{method}")

        if not scores:
            print("No results.")
            continue

        for metric in scores[0]:

            average_score = mean(
                item[metric] for item in scores
            )

            print(f"  {metric}: {average_score:.4f}")

    # -------------------------------------------------
    # FINAL ANSWER QUALITY BENCHMARK
    # -------------------------------------------------

    print("\n" + "=" * 65)
    print("ANSWER QUALITY BENCHMARK")
    print("=" * 65)

    print(
        f"Successful evaluations: "
        f"{len(answer_results)}/{len(BENCHMARK_QUESTIONS)}"
    )

    print(f"Failed evaluations: {len(failed_answers)}")

    answer_metrics = [
        "faithfulness",
        "answer_relevance",
        "completeness",
        "citation_correctness",
        "overall_score",
    ]

    if answer_results:

        for metric in answer_metrics:

            average_score = mean(
                result[metric] for result in answer_results
            )

            print(f"{metric}: {average_score:.2f}/5")

    else:
        print("No answer-quality results available.")

    if failed_answers:

        print("\nFAILED QUESTIONS:")

        for failure in failed_answers:
            print(f"- {failure['question']}")
            print(f"  Error: {failure['error']}")

    print("\nRAG BENCHMARK COMPLETED.")

    return {
        "retrieval_results": retrieval_results,
        "answer_results": answer_results,
        "failed_answers": failed_answers,
    }
