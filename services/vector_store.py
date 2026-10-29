import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

load_dotenv()

INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]
API_KEY = os.environ["PINECONE_KEY"]

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

def load_vector_store(video_id:str):
    return PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=embeddings,
        namespace=video_id,
        pinecone_api_key=API_KEY
    )
    
def create_vector_store(chunks: list[Document], video_id: str):
    vector_store=load_vector_store(video_id)
    
    vector_store.add_documents(
        documents=chunks,
        ids=[f"{video_id}-{i}" for i in range(len(chunks))]
    )
    
    return vector_store

    
def search_transcript(video_id:str, query:str, k:int = 4):
    vector_store=load_vector_store(video_id)
    
    results=vector_store.similarity_search(query, k=k)
    
    return [{
        "text": doc.page_content,
        "metadata": doc.metadata
    } for doc in results]