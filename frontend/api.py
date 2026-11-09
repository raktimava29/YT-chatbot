import requests
import streamlit as st

API_BASE_URL = st.secrets["API_BASE_URL"].rstrip("/")


def index_video(video_id: str, language: str = "en"):
    response = requests.post(
        f"{API_BASE_URL}/transcript/index",
        json={
            "video_id": video_id,
            "language": language,
        },
        timeout=300,
    )
    response.raise_for_status()
    return response.json()


def ask_question(video_id: str, question: str):
    response = requests.post(
        f"{API_BASE_URL}/chat/ask",
        json={
            "video_id": video_id,
            "question": question,
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()