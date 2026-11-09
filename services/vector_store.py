import os
import logging
from functools import lru_cache

from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

load_dotenv()

logger = logging.getLogger(__name__)

BATCH_SIZE = 16


@lru_cache(maxsize=1)
def get_embeddings():
    logger.info("EMBEDDINGS: Loading model")

    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"batch_size": 1},
    )

    logger.info("EMBEDDINGS: Model loaded")
    return embeddings


@lru_cache(maxsize=1)
def get_pinecone():
    api_key = os.getenv("PINECONE_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")

    if not api_key or not index_name:
        raise RuntimeError("Missing Pinecone environment variables")

    logger.info("PINECONE: Connecting to index")

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
    logger.info("INDEX: Preparing Pinecone namespace")

    index = get_pinecone()
    stats = index.describe_index_stats()
    namespaces = stats.namespaces or {}

    if video_id in namespaces:
        logger.info("INDEX: Deleting existing namespace")
        index.delete(delete_all=True, namespace=video_id)

    logger.info("INDEX: Loading vector store and embeddings")

    vector_store = load_vector_store(video_id)

    total = len(chunks)

    logger.info("INDEX: Starting upload. Total chunks=%s", total)

    for start in range(0, total, BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]

        logger.info(
            "INDEX: Uploading chunks %s-%s of %s",
            start + 1,
            start + len(batch),
            total,
        )

        vector_store.add_documents(
            documents=batch,
            ids=[
                f"{video_id}-{i}"
                for i in range(start, start + len(batch))
            ],
        )

    logger.info("INDEX: All chunks uploaded successfully")

    return vector_store


def search_transcript(video_id: str, query: str, k: int = 4):
    vector_store = load_vector_store(video_id)

    results = vector_store.similarity_search(query, k=k)

    return [
        {
            "text": doc.page_content,
            "metadata": doc.metadata,
        }
        for doc in results
    ]