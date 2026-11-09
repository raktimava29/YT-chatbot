import os
import logging
from functools import lru_cache

import httpx
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

load_dotenv()

logger = logging.getLogger(__name__)

BATCH_SIZE = 16
EMBEDDING_MODEL = "embed-english-light-v3.0"
EMBEDDING_DIMENSION = 384
COHERE_URL = "https://api.cohere.com/v2/embed"


class CohereEmbeddings(Embeddings):
    def __init__(self):
        self.api_key = os.getenv("COHERE_API_KEY")

        if not self.api_key:
            raise RuntimeError("Missing COHERE_API_KEY")

        self.client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def _embed(self, texts: list[str], input_type: str):
        if not texts:
            return []

        response = self.client.post(
            COHERE_URL,
            json={
                "model": EMBEDDING_MODEL,
                "texts": texts,
                "input_type": input_type,
                "embedding_types": ["float"],
            },
        )

        response.raise_for_status()

        vectors = response.json()["embeddings"]["float"]

        if any(len(vector) != EMBEDDING_DIMENSION for vector in vectors):
            raise RuntimeError("Unexpected Cohere embedding dimension")

        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = []

        for start in range(0, len(texts), 96):
            batch = texts[start:start + 96]
            embeddings.extend(
                self._embed(batch, "search_document")
            )

        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "search_query")[0]


@lru_cache(maxsize=1)
def get_embeddings():
    logger.info("EMBEDDINGS: Initializing Cohere client")
    return CohereEmbeddings()


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

    if stats.dimension != EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Pinecone dimension mismatch: expected {EMBEDDING_DIMENSION}, "
            f"got {stats.dimension}"
        )

    # Verify Cohere API before deleting existing vectors.
    logger.info("INDEX: Testing Cohere embeddings")

    embeddings = get_embeddings()
    embeddings.embed_query("Embedding connectivity test")

    logger.info("INDEX: Cohere embeddings ready")

    namespaces = stats.namespaces or {}

    if video_id in namespaces:
        logger.info("INDEX: Deleting old namespace")
        index.delete(delete_all=True, namespace=video_id)

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