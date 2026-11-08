import os
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from functools import lru_cache

load_dotenv()

@lru_cache(maxsize=1)
def get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"batch_size": 1},
    )

@lru_cache
def get_pinecone():
    api_key = os.getenv("PINECONE_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")

    if not api_key or not index_name:
        raise RuntimeError("Missing Pinecone environment variables")

    pc = Pinecone(api_key=api_key)
    return pc.Index(index_name)

def load_vector_store(video_id: str):
    index_name = os.getenv("PINECONE_INDEX_NAME")
    api_key = os.getenv("PINECONE_KEY")

    if not index_name or not api_key:
        raise RuntimeError("Missing Pinecone environment variables")

    return PineconeVectorStore(
        index_name=index_name,
        embedding=get_embeddings(),
        namespace=video_id,
        pinecone_api_key=api_key,
    )
    
def create_vector_store(chunks: list[Document], video_id: str):
    vector_store=load_vector_store(video_id)
    index = get_pinecone()
    stats = index.describe_index_stats()
    namespaces = stats.namespaces or {}
    
    if video_id in namespaces:
        vector_store.delete(
            delete_all=True,
            namespace=video_id,
        )
    
    vector_store.add_documents(
        documents=chunks,
        ids=[f"{video_id}-{i}" for i in range(len(chunks))]
    )
    
    return vector_store

    
def search_transcript(video_id:str, query:str, k:int = 4):
    vector_store=load_vector_store(video_id)
    
    results=vector_store.similarity_search(query, k=k)
    
    return [
        {
            "text": doc.page_content,
            "metadata": doc.metadata
        } for doc in results
    ]