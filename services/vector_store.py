from langchain_huggingface import HuggingFaceEmbeddings
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

INDEX_DIR = Path("faiss_idx")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

def create_vector_store(chunks: list[Document], video_id: str):
    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings
    )
    
    save_path = INDEX_DIR/video_id
    save_path.mkdir(parents=True, exist_ok=True)
    
    vector_store.save_local(str(save_path))
    
    return vector_store

def load_vector_store(video_id:str):
    index_path = INDEX_DIR/video_id
    
    if not index_path.exists():
        raise FileNotFoundError("FAISS index not found")
    
    return FAISS.load_local(
        str(index_path),
        embeddings,
        allow_dangerous_deserialization=True
    )
    
def search_transcript(video_id:str, query:str, k:int = 4):
    vector_store=load_vector_store(video_id)
    
    results=vector_store.similarity_search(query, k=k)
    
    return [{
        "text": doc.page_content,
        "metadata": doc.metadata
    } for doc in results]