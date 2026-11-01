from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from services.vector_store import index, embeddings

class PineconeRetriever(BaseRetriever):
    index:object = Field(exclude=True)
    embeddings:object = Field(exclude=True)
    
    video_id:str
    k:int = 20
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def _get_relevant_documents(self, query:str):
        query_vector = self.embeddings.embed_query(query)
        
        results = self.index.query(
            vector=query_vector,
            top_k=self.k,
            namespace=self.video_id,
            include_metadata=True
        )
        
        documents = []
        
        for match in results.matches:
            metadata = match.metadata or {}
            
            documents.append(
                Document(
                    page_content=metadata.get("text", ""),
                    metadata={
                        "video_id": self.video_id,
                        "chunk_id": match.id,
                        "score": match.score,
                        "start_time": metadata.get("start_time"),
                        "end_time": metadata.get("end_time"),
                        "language": metadata.get("language"),
                    },
                )
            )
            
        return documents
    
def get_retriever(video_id:str, k:int = 20):
    return PineconeRetriever(
        index=index,
        embeddings=embeddings,
        video_id=video_id,
        k=k
    )