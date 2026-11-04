from fastapi.testclient import TestClient

from main import app
from routers import chat_router


client = TestClient(app)


def test_valid_question(monkeypatch):
    def mock_ask_video(video_id, question):
        return {
            "answer": "Micrograd implements backpropagation.",
            "sources": [],
        }

    monkeypatch.setattr(
        chat_router,
        "ask_video",
        mock_ask_video,
    )

    response = client.post(
        "/chat/ask",
        json={
            "video_id": "VMj-3S1tku0",
            "question": "What is micrograd?",
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == (
        "Micrograd implements backpropagation."
    )


def test_empty_question():
    response = client.post(
        "/chat/ask",
        json={
            "video_id": "VMj-3S1tku0",
            "question": "",
        },
    )

    assert response.status_code == 422


def test_missing_video_id():
    response = client.post(
        "/chat/ask",
        json={
            "question": "What is micrograd?",
        },
    )

    assert response.status_code == 422


def test_missing_question():
    response = client.post(
        "/chat/ask",
        json={
            "video_id": "VMj-3S1tku0",
        },
    )

    assert response.status_code == 422


def test_whitespace_question():
    response = client.post(
        "/chat/ask",
        json={
            "video_id": "VMj-3S1tku0",
            "question": "   ",
        },
    )

    assert response.status_code == 422


def test_whitespace_video_id():
    response = client.post(
        "/chat/ask",
        json={
            "video_id": "   ",
            "question": "What is micrograd?",
        },
    )

    assert response.status_code == 422


def test_invalid_request_body():
    response = client.post(
        "/chat/ask",
        json={
            "video_id": 123,
            "question": "What is micrograd?",
        },
    )

    assert response.status_code == 422


def test_rag_service_failure(monkeypatch):
    def mock_ask_video(video_id, question):
        raise RuntimeError("Test service failure")

    monkeypatch.setattr(
        chat_router,
        "ask_video",
        mock_ask_video,
    )

    response = client.post(
        "/chat/ask",
        json={
            "video_id": "VMj-3S1tku0",
            "question": "What is micrograd?",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Test service failure"