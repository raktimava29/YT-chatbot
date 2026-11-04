import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from services.reranker import retrieve_and_rerank


load_dotenv()

llm = ChatGroq(
    model="qwen/qwen3.8-27b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)


prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a helpful assistant answering questions about YouTube videos.

Answer using ONLY the provided transcript context.

Rules:
1. Do not use external knowledge.
2. Do not invent information.
3. If context does not contain answer, clearly say:
   "This information is not available in the video transcript."
4. Give clear, concise answers.
5. Explain technical concepts using context provided.
6. Do not mention retrieval or reranking.
7. When relevant, mention timestamp references from the provided context
   using [HH:MM:SS] format.
8. Only use timestamps explicitly provided in the context.
   Never invent timestamps.
9. Place timestamp references directly beside the claims they support.
   Do not append a separate timestamp list at the end.
"""
    ),
    (
        "human",
        """
Transcript context:

{context}

Question:
{question}

Answer:
"""
    )
])

rag_chain = prompt | llm | StrOutputParser()


def format_timestamp(seconds: float) -> str:
    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def ask_video(
    video_id: str,
    question: str,
):
    results = retrieve_and_rerank(
        video_id=video_id,
        query=question,
        top_k=4,
        candidate_k=20,
    )

    unavailable_message = (
        "This information is not available in the video transcript."
    )

    if not results:
        return {
            "answer": unavailable_message,
            "sources": [],
        }

    best_score = float(results[0][1])

    # Temporary threshold based on notebook experiments.
    if best_score < -5.0:
        return {
            "answer": unavailable_message,
            "sources": [],
        }

    # Build timestamp-aware context for LLM.
    context_parts = []

    for doc, score in results:
        start_time = doc.metadata.get("start_time")
        end_time = doc.metadata.get("end_time")

        if start_time is not None and end_time is not None:
            timestamp = (
                f"[{format_timestamp(start_time)} - "
                f"{format_timestamp(end_time)}]"
            )
        else:
            timestamp = "[Timestamp unavailable]"

        context_parts.append(
            f"{timestamp}\n{doc.page_content}"
        )

    context = "\n\n".join(context_parts)

    answer = rag_chain.invoke({
        "context": context,
        "question": question,
    })

    # Keep source metadata separate from LLM context.
    sources = []

    for doc, score in results:
        start_time = doc.metadata.get("start_time")
        end_time = doc.metadata.get("end_time")

        source = {
            "chunk_id": doc.metadata["chunk_id"],
            "score": round(float(score), 4),
            "content": doc.page_content,
            "start_time": start_time,
            "end_time": end_time,
        }

        if start_time is not None:
            source["youtube_url"] = (
                f"https://www.youtube.com/watch?v={video_id}"
                f"&t={int(start_time)}s"
            )

        sources.append(source)

    return {
        "answer": answer,
        "sources": sources,
    }