import os
import logging

import httpx

from services.retriever import get_retriever

logger = logging.getLogger(__name__)

COHERE_RERANK_URL = "https://api.cohere.com/v2/rerank"
COHERE_RERANK_MODEL = "rerank-v3.5"


def rerank_documents(query, documents, top_k=4):
    if not documents:
        return []

    api_key = os.getenv("COHERE_API_KEY")

    if not api_key:
        raise RuntimeError("Missing COHERE_API_KEY")

    logger.info(
        "RERANK: Sending %s documents to Cohere",
        len(documents),
    )

    response = httpx.post(
        COHERE_RERANK_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": COHERE_RERANK_MODEL,
            "query": query,
            "documents": [
                doc.page_content for doc in documents
            ],
            "top_n": min(top_k, len(documents)),
        },
        timeout=60.0,
    )

    response.raise_for_status()

    results = response.json()["results"]

    ranked = [
        (
            documents[item["index"]],
            item["relevance_score"],
        )
        for item in results
    ]

    logger.info(
        "RERANK: Cohere returned %s ranked documents",
        len(ranked),
    )

    return ranked


def retrieve_and_rerank(
    video_id: str,
    query: str,
    top_k: int = 4,
    candidate_k: int = 20,
):
    logger.info("RETRIEVER: Fetching %s candidates", candidate_k)

    retriever = get_retriever(
        video_id=video_id,
        k=candidate_k,
    )

    documents = retriever.invoke(query)

    logger.info(
        "RETRIEVER: Retrieved %s documents",
        len(documents),
    )

    if not documents:
        return []

    return rerank_documents(
        query=query,
        documents=documents,
        top_k=top_k,
    )