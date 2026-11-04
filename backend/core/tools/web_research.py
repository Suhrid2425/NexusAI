import logging
import os

from tavily import TavilyClient

logger = logging.getLogger(__name__)


class WebResearchError(Exception):
    """Raised when web research cannot be completed."""


def web_research(
    query: str,
    max_results: int = 5,
) -> dict:
    """
    Search the web using Tavily and return structured research results.

    Args:
        query: User's research question.
        max_results: Maximum number of search results.

    Returns:
        Dictionary containing search results and metadata.
    """

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        raise WebResearchError(
            "TAVILY_API_KEY is not configured."
        )

    if not query or not query.strip():
        raise WebResearchError(
            "Search query cannot be empty."
        )

    try:
        client = TavilyClient(api_key=api_key)

        response = client.search(
            query=query.strip(),
            search_depth="advanced",
            max_results=max_results,
            include_answer=False,
            include_raw_content=False,
        )

        results = []

        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score", 0),
            })

        logger.info(
            "Web research completed. Query=%s Results=%s",
            query,
            len(results),
        )

        return {
            "success": True,
            "query": query,
            "result_count": len(results),
            "results": results,
        }

    except Exception as error:
        logger.exception("Tavily web research failed.")

        raise WebResearchError(
            f"Web research failed: {error}"
        ) from error