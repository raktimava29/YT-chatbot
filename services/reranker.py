from sentence_transformers import CrossEncoder
from services.retriever import get_retriever
from functools import lru_cache

@lru_cache
def get_reranker():
    return CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

def rerank_documents(query, documents):
    pairs = [
        (query, doc.page_content) for doc in documents
    ]
    
    scores = get_reranker().predict(pairs)
    
    ranked = sorted(
        zip(documents, scores),
        key=lambda x: x[1],
        reverse=True
    )
    
    return ranked

def filter_relevant_documents(ranked_docs, threshold=-5.0):
    return [
        (doc, score)
        for doc, score in ranked_docs
        if score >= threshold
    ]
    
def  retrieve_and_rerank(video_id:str, query: str, top_k:int = 4, candidate_k:int = 20):
    retriever = get_retriever(
        video_id=video_id,
        k=candidate_k
    )
    
    docs = retriever.invoke(query)
    
    if not docs:
        return []
    
    ranked_docs = rerank_documents(query, docs)
    
    return ranked_docs[:top_k]
    