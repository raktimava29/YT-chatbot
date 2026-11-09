import re
import streamlit as st

from api import index_video, ask_question

st.set_page_config(
    page_title="VidQuery",
    page_icon="▶",
    layout="wide",
)

st.title("VidQuery")
st.caption("Chat with YouTube videos using AI")

if "video_id" not in st.session_state:
    st.session_state.video_id = None

if "indexed" not in st.session_state:
    st.session_state.indexed = False

if "messages" not in st.session_state:
    st.session_state.messages = []


def extract_video_id(url: str):
    patterns = [
        r"(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


with st.sidebar:
    st.header("Video setup")

    video_url = st.text_input("YouTube URL")

    language = st.selectbox(
        "Transcript language",
        ["en", "hi", "es", "fr", "de"],
    )

    if st.button("Index video", use_container_width=True):
        video_id = extract_video_id(video_url)

        if not video_id:
            st.error("Invalid YouTube URL")
        else:
            try:
                with st.spinner("Fetching transcript and indexing video..."):
                    result = index_video(video_id, language)

                st.session_state.video_id = video_id
                st.session_state.indexed = True
                st.session_state.messages = []

                st.success(
                    f"Indexed {result['total_chunks']} chunks"
                )

            except Exception as exc:
                st.error(f"Indexing failed: {exc}")

    if st.session_state.indexed:
        st.success("Video indexed")

        if st.button("Clear video"):
            st.session_state.video_id = None
            st.session_state.indexed = False
            st.session_state.messages = []
            st.rerun()


if not st.session_state.indexed:
    st.info("Enter YouTube URL and index video to start chatting.")
    st.stop()


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.markdown(
                        f"**Score:** {source['score']}"
                    )
                    st.write(source["content"])

                    if source.get("youtube_url"):
                        st.link_button(
                            "Watch timestamp",
                            source["youtube_url"],
                        )


question = st.chat_input("Ask something about this video...")

if question:
    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    with st.chat_message("user"):
        st.markdown(question)

    try:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = ask_question(
                    st.session_state.video_id,
                    question,
                )

            st.markdown(result["answer"])

            with st.expander("Sources"):
                for source in result.get("sources", []):
                    st.write(source["content"])

                    if source.get("youtube_url"):
                        st.link_button(
                            "Watch timestamp",
                            source["youtube_url"],
                        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("sources", []),
        })

    except Exception as exc:
        st.error(f"Request failed: {exc}")