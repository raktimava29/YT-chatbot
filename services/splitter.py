from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_transcript(transcript: list[dict], video_id: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    documents = []
    current_text = []
    current_start = None
    current_end = None

    for snippet in transcript:
        if current_start is None:
            current_start = snippet["start"]

        current_text.append(snippet["text"])
        current_end = snippet["end"]

        text = " ".join(current_text)

        if len(text) >= 1000:
            split_texts = splitter.split_text(text)

            for chunk in split_texts:
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            "video_id": video_id,
                            "start_time": current_start,
                            "end_time": current_end,
                        },
                    )
                )

            current_text = []
            current_start = None
            current_end = None

    if current_text:
        documents.append(
            Document(
                page_content=" ".join(current_text),
                metadata={
                    "video_id": video_id,
                    "start_time": current_start,
                    "end_time": current_end,
                },
            )
        )

    return documents