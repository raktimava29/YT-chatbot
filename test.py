# from services.retriever import get_retriever

# video_id = "VMj-3S1tku0"

# retriever = get_retriever(video_id, k=20)

# docs = retriever.invoke("What is micrograd and how does it work?")

# for doc in docs[:3]:
#     print("Chunk ID:", doc.metadata["chunk_id"])
#     print("Score:", doc.metadata["score"])
#     print("Start:", doc.metadata["start_time"])
#     print("End:", doc.metadata["end_time"])
#     print("Text:", doc.page_content[:200])
#     print("-" * 50)


from services.reranker import retrieve_and_rerank

video_id = "VMj-3S1tku0"

question = "What is micrograd and how does it work?"

results = retrieve_and_rerank(
    video_id=video_id,
    query=question,
    top_k=4,
    candidate_k=20,
)

for i, (doc, score) in enumerate(results, start=1):
    print(f"\n--- Result {i} ---")
    print("Reranker score:", round(float(score), 4))
    print("Chunk ID:", doc.metadata["chunk_id"])
    print("Start:", doc.metadata["start_time"])
    print("End:", doc.metadata["end_time"])
    print("Content:", doc.page_content[:300])