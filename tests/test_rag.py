import pytest

from langchain_core.documents import Document

from services import rag


UNAVAILABLE_MESSAGE = (
    "This information is not available in the video transcript."
)


@pytest.fixture
def sample_document():
    return Document(
        page_content="Micrograd is an autograd engine.",
        metadata={
            "video_id": "VMj-3S1tku0",
            "chunk_id": "VMj-3S1tku0-1",
            "start_time": 40.64,
            "end_time": 103.28,
            "language": "en",
        },
    )


def test_no_retrieved_documents(monkeypatch):
    monkeypatch.setattr(
        rag,
        "retrieve_and_rerank",
        lambda **kwargs: [],
    )

    result = rag.ask_video(
        video_id="VMj-3S1tku0",
        question="What is micrograd?",
    )

    assert result["answer"] == UNAVAILABLE_MESSAGE
    assert result["sources"] == []


def test_low_reranker_score(monkeypatch, sample_document):
    monkeypatch.setattr(
        rag,
        "retrieve_and_rerank",
        lambda **kwargs: [
            (sample_document, -6.0)
        ],
    )

    result = rag.ask_video(
        video_id="VMj-3S1tku0",
        question="What is nuclear fusion?",
    )

    assert result["answer"] == UNAVAILABLE_MESSAGE
    assert result["sources"] == []


def test_relevant_documents(monkeypatch, sample_document):
    expected_answer = (
        "Micrograd is an autograd engine that implements backpropagation."
    )

    monkeypatch.setattr(
        rag,
        "retrieve_and_rerank",
        lambda **kwargs: [
            (sample_document, 5.2051)
        ],
    )

    class MockRAGChain:
        def invoke(self, inputs):
            assert inputs["question"] == "What is micrograd?"
            assert "[00:00:40 - 00:01:43]" in inputs["context"]
            assert "Micrograd is an autograd engine." in inputs["context"]

            return expected_answer

    monkeypatch.setattr(
        rag,
        "rag_chain",
        MockRAGChain(),
    )

    result = rag.ask_video(
        video_id="VMj-3S1tku0",
        question="What is micrograd?",
    )

    assert result["answer"] == expected_answer
    assert len(result["sources"]) == 1

    source = result["sources"][0]

    assert source["chunk_id"] == "VMj-3S1tku0-1"
    assert source["score"] == 5.2051
    assert source["start_time"] == 40.64
    assert source["end_time"] == 103.28

    assert source["youtube_url"] == (
        "https://www.youtube.com/watch?v=VMj-3S1tku0&t=40s"
    )


def test_source_metadata_without_timestamps(monkeypatch):
    document = Document(
        page_content="Micrograd implements backpropagation.",
        metadata={
            "video_id": "VMj-3S1tku0",
            "chunk_id": "VMj-3S1tku0-2",
        },
    )

    monkeypatch.setattr(
        rag,
        "retrieve_and_rerank",
        lambda **kwargs: [
            (document, 2.5)
        ],
    )

    class MockRAGChain:
        def invoke(self, inputs):
            assert "[Timestamp unavailable]" in inputs["context"]
            return "Micrograd implements backpropagation."

    monkeypatch.setattr(
        rag,
        "rag_chain",
        MockRAGChain(),
    )

    result = rag.ask_video(
        video_id="VMj-3S1tku0",
        question="What does micrograd implement?",
    )

    assert result["answer"] == (
        "Micrograd implements backpropagation."
    )

    source = result["sources"][0]

    assert source["start_time"] is None
    assert source["end_time"] is None
    assert "youtube_url" not in source


def test_groq_generation_failure(monkeypatch, sample_document):
    monkeypatch.setattr(
        rag,
        "retrieve_and_rerank",
        lambda **kwargs: [
            (sample_document, 5.0)
        ],
    )

    class MockRAGChain:
        def invoke(self, inputs):
            raise RuntimeError("Groq API failure")

    monkeypatch.setattr(
        rag,
        "rag_chain",
        MockRAGChain(),
    )

    with pytest.raises(
        RuntimeError,
        match="Groq API failure",
    ):
        rag.ask_video(
            video_id="VMj-3S1tku0",
            question="What is micrograd?",
        )


def test_format_timestamp():
    assert rag.format_timestamp(40.64) == "00:00:40"
    assert rag.format_timestamp(189.36) == "00:03:09"
    assert rag.format_timestamp(3600) == "01:00:00"
    assert rag.format_timestamp(8077.28) == "02:14:37"