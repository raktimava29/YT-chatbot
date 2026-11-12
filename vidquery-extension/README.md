# VidQuery — YouTube AI Assistant

VidQuery is a Chromium Manifest V3 extension that lets you index a YouTube video's transcript and ask questions about it from a persistent browser side panel. Answers stream as they are generated and include timestamped transcript sources.

## Features

- Detects active YouTube videos, Shorts, and live videos.
- Indexes transcript content through the VidQuery FastAPI backend.
- Streams answers token by token using Server-Sent Events (SSE).
- Displays timestamp citations that open the matching YouTube position.
- Keeps sources collapsed until the user expands them.
- Supports multiple independent chat sessions per video.
- Automatically saves and restores conversations using `chrome.storage.local`.
- Remembers which videos have been indexed, avoiding unnecessary re-indexing when returning to a saved conversation.
- Suggested questions, Markdown-style answer rendering, copy, retry, and stop controls.

## Architecture

```text
Chrome / Brave Side Panel
        |
        v
React + TypeScript UI (Vite)
        |
        +---- chrome.tabs / chrome.storage.local
        |       |                    |
        |       |                    +-- sessions, messages, selected session,
        |       |                        indexed video IDs
        |       +-- active YouTube tab detection
        |
        +---- HTTPS / JSON ----------------------+
        |                                        |
        +---- HTTPS / SSE stream ----------------+
                                                 v
                                      FastAPI backend
                                                 |
                     +---------------------------+----------------------+
                     |                           |                      |
                     v                           v                      v
              Supadata transcript          Pinecone namespace      Groq LLM
                     |                     per YouTube video      via LangChain
                     v                           ^                      |
              Transcript chunks                  |                      |
                     |                            |                      |
                     +--> Hugging Face embeddings +                      |
                                                  |                      |
                                      Retriever + cross-encoder reranker  |
                                                  |                      |
                                                  +---- context ----------+
                                                                       |
                                                        SSE token/source events
                                                                       |
                                                                       v
                                                         Side panel chat UI
```

### Frontend

- React 19 + TypeScript
- Vite 6 build pipeline
- Tailwind CSS 4
- Chrome Extension Manifest V3
- `chrome.tabs` for active-tab detection
- `chrome.storage.local` for local chat/session persistence
- Fetch streaming reader for SSE events

### Backend

Backend is a separate FastAPI service. Its current pipeline uses:

1. Supadata to fetch YouTube transcript segments.
2. Transcript splitting into timestamped chunks.
3. `sentence-transformers/all-MiniLM-L6-v2` embeddings.
4. Pinecone namespaces keyed by YouTube video ID.
5. Retriever plus `cross-encoder/ms-marco-MiniLM-L-6-v2` reranking.
6. Groq `qwen/qwen3.8-27b` through LangChain for answer generation.
7. FastAPI `StreamingResponse` to send SSE events to the extension.

## Requirements

- Node.js 20 or newer (Node.js 22 recommended)
- npm
- Google Chrome 116+ or a compatible Chromium browser such as Brave
- Access to deployed VidQuery backend, or your own configured backend

## Local setup

```bash
git clone <your-extension-repository-url>
cd <extension-project-directory>
npm install
```

Create local environment file:

```bash
cp .env.example .env
```

Set backend URL if using a non-default deployment:

```env
VITE_API_BASE_URL=https://your-backend.example.com
```

Default backend URL is:

```text
https://vidquery-npa6.onrender.com
```

`VITE_API_BASE_URL` is a build-time frontend setting. If you change it to a different host, add that host to `host_permissions` in `extension/manifest.json` before building.

## Production build

```bash
npm run build
```

Build output is written to `dist/`. The build script copies `extension/manifest.json` and `extension/background.js` into `dist/`.

## Load unpacked extension

1. Open `chrome://extensions` in Chrome or `brave://extensions` in Brave.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the generated `dist/` directory.
5. Open a YouTube video and click VidQuery toolbar icon to open side panel.

After rebuilding, return to the extensions page and click **Reload** on VidQuery.

## Backend configuration

Backend requires these environment variables:

```env
SUPADATA_API_KEY=your_supadata_api_key
GROQ_API_KEY=your_groq_api_key
PINECONE_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
```

Pinecone index must use embedding dimension **384**, matching `sentence-transformers/all-MiniLM-L6-v2`.

Install backend dependencies using its `requirements.txt` or `pyproject.toml`, then run from backend project root:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Do not commit real API keys or `.env` files.

## API contract

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/transcript/index` | Fetch transcript, split it, embed chunks, and store them in Pinecone. |
| `POST` | `/chat/ask` | Return complete JSON answer and sources (backward-compatible endpoint). |
| `POST` | `/chat/stream` | Stream answer tokens and sources as SSE. |

### Index request

```json
{
  "video_id": "YOUTUBE_VIDEO_ID",
  "language": "en"
}
```

### Streaming chat request

```json
{
  "video_id": "YOUTUBE_VIDEO_ID",
  "question": "Summarize this video"
}
```

SSE event payloads:

- `{"type":"token","content":"..."}` — append generated text.
- `{"type":"sources","sources":[...]}` — timestamp citations, sent after generation.
- `{"type":"done"}` — generation completed.
- `{"type":"error","detail":"..."}` — generation failed.

## Local data and privacy

Chat sessions, messages, selected session IDs, and indexed-video markers are stored in the browser's extension-local storage. They are not sent to the backend for persistence. The backend receives video IDs and questions for transcript indexing and answer generation. Transcript chunks and embeddings are stored in the configured Pinecone index.

## Project structure

```text
.
├── app/
│   ├── components/VideoDetection.tsx
│   ├── hooks/useActiveYouTubeVideo.ts
│   ├── lib/api.ts
│   ├── lib/storage.ts
│   ├── lib/youtube.ts
│   ├── types/index.ts
│   └── globals.css
├── extension/
│   ├── background.js
│   └── manifest.json
├── scripts/copy-extension.mjs
├── src/main.tsx
├── index.html
├── vite.config.ts
├── package.json
└── .env.example
```

## Troubleshooting

- **Backend connection error:** open backend root URL in browser and confirm service is awake; verify `VITE_API_BASE_URL` and rebuild.
- **Extension cannot access custom backend:** add its origin to `host_permissions` in `extension/manifest.json`, then rebuild and reload.
- **Streaming endpoint returns 404:** deploy backend revision containing `/chat/stream` before rebuilding or testing extension.
- **No transcript available:** video must expose a transcript supported by Supadata.
- **Old UI after build:** reload extension from `chrome://extensions` / `brave://extensions`; reopen side panel.
- **Chat history missing:** verify extension was reloaded in same browser profile; storage is browser-profile local.