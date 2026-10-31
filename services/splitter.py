from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_transcript(transcript: list[dict], video_id: str, chunk_size: int = 1000, chunk_overlap: int = 200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )

    text_parts = []
    snippet_ranges = []
    cursor = 0

    for snippet in transcript:
        snippet_text = snippet["text"]

        start_offset = cursor
        end_offset = start_offset + len(snippet_text)

        text_parts.append(snippet_text)

        snippet_ranges.append({
            "start_offset": start_offset,
            "end_offset": end_offset,
            "start_time": snippet["start"],
            "end_time": snippet["end"],
        })

        cursor = end_offset + 1

    full_text = " ".join(text_parts)

    # Split text and retain original character offsets.
    split_documents = splitter.create_documents([full_text])

    documents = []

    for chunk in split_documents:
        chunk_start = chunk.metadata["start_index"]
        chunk_end = chunk_start + len(chunk.page_content)

        overlapping_snippets = [
            snippet
            for snippet in snippet_ranges
            if (
                snippet["start_offset"] < chunk_end
                and snippet["end_offset"] > chunk_start
            )
        ]

        if not overlapping_snippets:
            continue

        documents.append(
            Document(
                page_content=chunk.page_content,
                metadata={
                    "video_id": video_id,
                    "start_time": overlapping_snippets[0]["start_time"],
                    "end_time": overlapping_snippets[-1]["end_time"],
                },
            )
        )

    return documents