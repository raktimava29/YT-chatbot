import gc
from functools import lru_cache

from services.retriever import get_retriever


@lru_cache(maxsize=1)
def get_reranker():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device="cpu",
    )


def rerank_documents(query, documents):
    pairs = [
        (query, doc.page_content) for doc in documents
    ]

    scores = get_reranker().predict(
        pairs,
        batch_size=1,
    )

    ranked = sorted(
        zip(documents, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    return ranked


def retrieve_and_rerank(video_id: str, query: str, top_k: int = 4, candidate_k: int = 20):
    from services.vector_store import get_embeddings

    retriever = get_retriever(
        video_id=video_id,
        k=candidate_k,
    )

    docs = retriever.invoke(query)

    del retriever
    get_embeddings.cache_clear()
    gc.collect()

    if not docs:
        return []

    ranked_docs = rerank_documents(query, docs)

    return ranked_docs[:top_k]