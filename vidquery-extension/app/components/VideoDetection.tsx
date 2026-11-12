import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useActiveYouTubeVideo } from "../hooks/useActiveYouTubeVideo";
import { indexTranscript, streamVideoAnswer, type ChatSource } from "../lib/api";
import {
  getIndexedVideos,
  getSelectedSessions,
  getSessions,
  markVideoIndexed,
  removeSession,
  saveSession,
  setSelectedSession,
} from "../lib/storage";
import type { ChatMessage, ChatSession } from "../types";


function renderInlineMarkdown(text: string) {
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g);
  return tokens.map((token, index) => {
    if (token.startsWith("**") && token.endsWith("**")) return <strong key={index}>{token.slice(2, -2)}</strong>;
    if (token.startsWith("`") && token.endsWith("`")) return <code key={index} className="rounded bg-black/30 px-1 py-0.5 text-[0.92em]">{token.slice(1, -1)}</code>;
    if (token.startsWith("*") && token.endsWith("*")) return <em key={index}>{token.slice(1, -1)}</em>;
    return token;
  });
}

function MarkdownAnswer({ content }: { content: string }) {
  const blocks = content.split(/```/g);
  return <div className="space-y-2 break-words text-xs leading-5">
    {blocks.map((block, blockIndex) => {
      if (blockIndex % 2 === 1) {
        const lines = block.split("\n");
        const hasLanguageLabel = lines.length > 1 && /^[a-zA-Z0-9_+-]+$/.test(lines[0].trim());
        const code = hasLanguageLabel ? lines.slice(1).join("\n") : block;
        return <pre key={blockIndex} className="overflow-x-auto rounded-lg bg-black/40 p-3 text-[11px] leading-5"><code>{code.trim()}</code></pre>;
      }
      return block.split(/\n{2,}/).map((paragraph, paragraphIndex) => {
        const lines = paragraph.split("\n");
        const heading = lines.length === 1 ? /^(#{1,3})\s+(.+)$/.exec(lines[0]) : null;
        if (heading) return <p key={`${blockIndex}-${paragraphIndex}`} className="font-semibold text-white">{renderInlineMarkdown(heading[2])}</p>;
        const listLines = lines.filter((line) => /^\s*(?:[-*] |\d+\. )/.test(line));
        if (listLines.length === lines.length && listLines.length > 0) {
          return <ul key={`${blockIndex}-${paragraphIndex}`} className="list-disc space-y-1 pl-4">{listLines.map((line, index) => <li key={index}>{renderInlineMarkdown(line.replace(/^\s*(?:[-*] |\d+\. )/, ""))}</li>)}</ul>;
        }
        return <p key={`${blockIndex}-${paragraphIndex}`} className="whitespace-pre-wrap">{lines.map((line, index) => <span key={index}>{index > 0 ? "\n" : ""}{renderInlineMarkdown(line)}</span>)}</p>;
      });
    })}
  </div>;
}

const SUGGESTED_QUESTIONS = [
  "Summarize this video",
  "What are the key takeaways?",
  "Explain the main concepts",
  "What examples does the speaker give?",
];

function formatTimestamp(seconds: number): string {
  const value = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const remainingSeconds = value % 60;
  return [hours, minutes, remainingSeconds].map((part) => String(part).padStart(2, "0")).join(":");
}

function createSession(video: NonNullable<ReturnType<typeof useActiveYouTubeVideo>["video"]>): ChatSession {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    videoId: video.videoId,
    videoTitle: video.title,
    thumbnailUrl: video.thumbnailUrl,
    title: "New chat",
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
}

export default function VideoDetection() {
  const { video, status, error, refresh } = useActiveYouTubeVideo();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedByVideo, setSelectedByVideo] = useState<Record<string, string>>({});
  const [sessionReady, setSessionReady] = useState(false);
  const [indexedVideos, setIndexedVideos] = useState<string[]>([]);
  const [indexing, setIndexing] = useState(false);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [indexedChunks, setIndexedChunks] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [failedQuestion, setFailedQuestion] = useState<string | null>(null);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getSessions(), getSelectedSessions(), getIndexedVideos()]).then(([storedSessions, selected, indexed]) => {
      if (cancelled) return;
      setSessions(storedSessions);
      setSelectedByVideo(selected);
      setIndexedVideos(indexed);
      setSessionReady(true);
    }).catch((err) => {
      if (!cancelled) {
        setChatError(err instanceof Error ? err.message : "Could not restore saved chats.");
        setSessionReady(true);
      }
    });
    return () => { cancelled = true; };
  }, []);

  const videoSessions = useMemo(
    () => sessions.filter((session) => session.videoId === video?.videoId).sort((a, b) => b.updatedAt - a.updatedAt),
    [sessions, video?.videoId],
  );
  const activeSession = videoSessions.find((session) => session.id === selectedByVideo[video?.videoId ?? ""]) ?? videoSessions[0] ?? null;
  const messages = activeSession?.messages ?? [];
  const isIndexed = Boolean(video && indexedVideos.includes(video.videoId));

  useEffect(() => {
    if (!sessionReady || !video) return;
    let cancelled = false;
    const ensureSession = async () => {
      const existing = sessions.filter((session) => session.videoId === video.videoId);
      const preferredId = selectedByVideo[video.videoId];
      const preferred = existing.find((session) => session.id === preferredId) ?? existing.sort((a, b) => b.updatedAt - a.updatedAt)[0];
      if (preferred) {
        if (preferred.id !== preferredId) {
          await setSelectedSession(video.videoId, preferred.id);
          if (!cancelled) setSelectedByVideo((current) => ({ ...current, [video.videoId]: preferred.id }));
        }
        return;
      }
      const fresh = createSession(video);
      await saveSession(fresh);
      await setSelectedSession(video.videoId, fresh.id);
      if (!cancelled) {
        setSessions((current) => [...current, fresh]);
        setSelectedByVideo((current) => ({ ...current, [video.videoId]: fresh.id }));
      }
    };
    void ensureSession();
    return () => { cancelled = true; };
  }, [sessionReady, video?.videoId]); // Session selection is reconciled when active video changes.

  useEffect(() => {
    if (!sessionReady || !activeSession) return;
    const timer = window.setTimeout(() => {
      void saveSession({ ...activeSession, updatedAt: Date.now() });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [sessionReady, activeSession?.id, activeSession?.messages]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, asking]);

  const updateActiveSession = useCallback((updater: (session: ChatSession) => ChatSession) => {
    if (!activeSession) return;
    setSessions((current) => current.map((session) => session.id === activeSession.id ? updater(session) : session));
  }, [activeSession]);

  async function handleIndex() {
    if (!video || indexing) return;
    setIndexing(true);
    setIndexError(null);
    try {
      const result = await indexTranscript(video.videoId, "en");
      await markVideoIndexed(video.videoId);
      setIndexedVideos((current) => current.includes(video.videoId) ? current : [...current, video.videoId]);
      setIndexedChunks(result.total_chunks);
    } catch (err) {
      setIndexError(err instanceof Error ? err.message : "Transcript indexing failed.");
    } finally {
      setIndexing(false);
    }
  }

  async function sendQuestion(rawQuestion: string, appendUserMessage = true) {
    const trimmedQuestion = rawQuestion.trim();
    if (!video || !activeSession || !trimmedQuestion || asking || !isIndexed) return;
    if (appendUserMessage) {
      const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: trimmedQuestion, createdAt: Date.now() };
      updateActiveSession((session) => ({ ...session, title: session.messages.length === 0 ? trimmedQuestion.slice(0, 42) : session.title, messages: [...session.messages, userMessage], updatedAt: Date.now() }));
    }
    setQuestion("");
    setAsking(true);
    setChatError(null);
    setFailedQuestion(null);
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const assistantMessageId = crypto.randomUUID();
    let streamedContent = "";
    updateActiveSession((session) => ({
      ...session,
      messages: [...session.messages, {
        id: assistantMessageId, role: "assistant", content: "", sources: [], createdAt: Date.now(),
      }],
      updatedAt: Date.now(),
    }));
    try {
      await streamVideoAnswer(video.videoId, trimmedQuestion, {
        onToken: (token) => {
          streamedContent += token;
          updateActiveSession((session) => ({
            ...session,
            messages: session.messages.map((message) => message.id === assistantMessageId
              ? { ...message, content: streamedContent } : message),
            updatedAt: Date.now(),
          }));
        },
        onSources: (sources) => {
          updateActiveSession((session) => ({
            ...session,
            messages: session.messages.map((message) => message.id === assistantMessageId
              ? { ...message, sources } : message),
            updatedAt: Date.now(),
          }));
        },
      }, controller.signal);
      if (!streamedContent) {
        updateActiveSession((session) => ({ ...session, messages: session.messages.filter((message) => message.id !== assistantMessageId) }));
      }
    } catch (err) {
      if (!streamedContent) {
        updateActiveSession((session) => ({ ...session, messages: session.messages.filter((message) => message.id !== assistantMessageId) }));
      }
      if (err instanceof DOMException && err.name === "AbortError") {
        setChatError(streamedContent ? "Response stopped. Partial answer saved." : "Response stopped.");
        setFailedQuestion(trimmedQuestion);
      } else {
        setChatError(err instanceof Error ? err.message : "Could not get answer.");
        setFailedQuestion(trimmedQuestion);
      }
    } finally {
      if (abortControllerRef.current === controller) abortControllerRef.current = null;
      setAsking(false);
    }
  }

  function stopGeneration() {
    abortControllerRef.current?.abort();
  }

  async function copyAnswer(message: ChatMessage) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedMessageId(message.id);
      window.setTimeout(() => setCopiedMessageId((current) => current === message.id ? null : current), 1400);
    } catch {
      setChatError("Could not copy answer. Check clipboard permission.");
    }
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await sendQuestion(question);
  }

  async function handleNewSession() {
    if (!video) return;
    const fresh = createSession(video);
    await saveSession(fresh);
    await setSelectedSession(video.videoId, fresh.id);
    setSessions((current) => [...current, fresh]);
    setSelectedByVideo((current) => ({ ...current, [video.videoId]: fresh.id }));
    setChatError(null);
  }

  async function handleSelectSession(sessionId: string) {
    if (!video) return;
    await setSelectedSession(video.videoId, sessionId);
    setSelectedByVideo((current) => ({ ...current, [video.videoId]: sessionId }));
    setChatError(null);
  }

  async function handleDeleteSession(sessionId: string) {
    if (!video) return;
    await removeSession(sessionId);
    const remaining = videoSessions.filter((session) => session.id !== sessionId);
    setSessions((current) => current.filter((session) => session.id !== sessionId));
    if (remaining.length > 0) {
      await handleSelectSession(remaining[0].id);
    } else {
      const fresh = createSession(video);
      await saveSession(fresh);
      await setSelectedSession(video.videoId, fresh.id);
      setSessions((current) => [...current, fresh]);
      setSelectedByVideo((current) => ({ ...current, [video.videoId]: fresh.id }));
    }
  }

  async function handleRenameSession() {
    const title = renameValue.trim();
    if (!title || !activeSession) return;
    updateActiveSession((session) => ({ ...session, title, updatedAt: Date.now() }));
    await saveSession({ ...activeSession, title, updatedAt: Date.now() });
    setRenaming(false);
  }

  const sourceUrl = (source: ChatSource) => {
    if (source.youtube_url) return source.youtube_url;
    if (source.start_time !== null && video) return `${video.url}${video.url.includes("?") ? "&" : "?"}t=${Math.floor(source.start_time)}s`;
    return video?.url ?? "#";
  };

  return (
    <main className="flex min-h-screen flex-col bg-[#0b0d12] text-white">
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-4">
        <div><p className="text-lg font-semibold tracking-tight">VidQuery</p><p className="text-xs text-slate-400">Your YouTube AI assistant</p></div>
        <button type="button" onClick={() => void refresh()} className="rounded-lg border border-white/15 px-3 py-2 text-xs text-slate-300 transition hover:bg-white/10">Refresh</button>
      </header>

      <section className="flex flex-1 flex-col gap-3 p-3">
        <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-400">
          <span className={`h-2 w-2 rounded-full ${status === "detected" ? "bg-emerald-400" : status === "loading" ? "bg-amber-400" : "bg-slate-500"}`} />
          {status === "detected" ? "Video detected" : status === "loading" ? "Checking active tab" : status === "unavailable" ? "Extension unavailable" : "No supported video"}
        </div>

        {video ? (
          <article className="overflow-hidden rounded-2xl border border-white/10 bg-[#141821] shadow-xl shadow-black/20">
            <div className="flex gap-3 p-3">
              <img src={video.thumbnailUrl} alt={`Thumbnail for ${video.title}`} className="h-16 w-28 rounded-lg object-cover" onError={(event) => { event.currentTarget.style.visibility = "hidden"; }} />
              <div className="min-w-0 flex-1"><h1 className="line-clamp-2 text-xs font-semibold leading-5">{video.title}</h1><p className="mt-1 break-all text-[10px] text-slate-500">{video.videoId}</p><a href={video.url} target="_blank" rel="noreferrer" className="mt-1 inline-flex text-[10px] text-red-300 hover:text-red-200">Open on YouTube ↗</a></div>
            </div>
            <div className="px-3 pb-3">
              <button type="button" onClick={() => void handleIndex()} disabled={indexing || isIndexed} className="w-full rounded-xl bg-red-500 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-red-400 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-slate-400">{indexing ? "Indexing transcript..." : isIndexed ? "Transcript indexed" : "Index this video"}</button>
              {indexing && <p className="mt-2 text-center text-[10px] text-amber-300">Fetching transcript and creating searchable chunks...</p>}
              {isIndexed && <p className="mt-2 text-center text-[10px] text-emerald-300">Ready to chat{indexedChunks ? ` · ${indexedChunks} chunks indexed` : " · restored from saved state"}</p>}
              {indexError && <p role="alert" className="mt-2 rounded-lg bg-red-400/10 p-2 text-[10px] text-red-200">{indexError}</p>}
            </div>
          </article>
        ) : (
          <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.03] px-5 py-8 text-center"><h1 className="text-sm font-semibold">{status === "loading" ? "Detecting video..." : "Open a YouTube video"}</h1><p className="mx-auto mt-2 max-w-xs text-xs leading-5 text-slate-400">{error ?? "Navigate to a YouTube watch page, Short, or live video. VidQuery detects active video automatically."}</p></div>
        )}

        {video && sessionReady && (
          <section className="flex min-h-[26rem] flex-1 flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#11151d]">
            <div className="flex items-center justify-between gap-2 border-b border-white/10 px-3 py-3">
              <div className="min-w-0 flex-1">
                {renaming ? <form className="flex gap-1" onSubmit={(event) => { event.preventDefault(); void handleRenameSession(); }}><input autoFocus value={renameValue} onChange={(event) => setRenameValue(event.target.value)} className="min-w-0 flex-1 rounded bg-black/30 px-2 py-1 text-xs outline-none" /><button className="text-[10px] text-emerald-300">Save</button></form> : <button type="button" onClick={() => { setRenameValue(activeSession?.title ?? ""); setRenaming(true); }} className="max-w-full truncate text-left text-xs font-semibold hover:text-red-200">{activeSession?.title ?? "Chat"} <span className="text-slate-500">✎</span></button>}
                <p className="mt-1 text-[10px] text-slate-500">{videoSessions.length} {videoSessions.length === 1 ? "chat" : "chats"} for this video</p>
              </div>
              <div className="flex shrink-0 gap-1"><button type="button" onClick={() => void handleNewSession()} className="rounded-lg bg-red-500/15 px-2.5 py-2 text-[10px] font-semibold text-red-200 hover:bg-red-500/25">+ New</button><button type="button" disabled={!activeSession} onClick={() => activeSession && void handleDeleteSession(activeSession.id)} className="rounded-lg border border-white/10 px-2 py-2 text-[10px] text-slate-400 hover:bg-white/10 disabled:opacity-40">Delete</button></div>
            </div>

            {videoSessions.length > 1 && <div className="flex gap-1.5 overflow-x-auto border-b border-white/10 px-3 py-2">{videoSessions.map((session) => <button key={session.id} type="button" onClick={() => void handleSelectSession(session.id)} className={`max-w-36 shrink-0 truncate rounded-lg px-2.5 py-1.5 text-[10px] ${activeSession?.id === session.id ? "bg-white/15 text-white" : "bg-white/[0.04] text-slate-400 hover:bg-white/10"}`}>{session.title}</button>)}</div>}

            <div ref={scrollRef} className="flex flex-1 flex-col gap-3 overflow-y-auto p-3">
              {!isIndexed && <div className="m-auto max-w-xs text-center text-xs leading-5 text-slate-500">Index video transcript first. Saved conversations remain available after indexing state is restored.</div>}
              {isIndexed && messages.length === 0 && <div className="my-auto"><p className="mb-3 text-center text-xs text-slate-400">Ask anything about this video.</p><div className="grid grid-cols-1 gap-2">{SUGGESTED_QUESTIONS.map((suggestion) => <button key={suggestion} type="button" onClick={() => void sendQuestion(suggestion)} disabled={asking} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-left text-[11px] text-slate-300 transition hover:border-red-400/30 hover:bg-red-500/5 disabled:opacity-50">{suggestion} <span className="float-right text-slate-600">↗</span></button>)}</div></div>}
              {messages.map((message) => <article key={message.id} className={`max-w-[96%] rounded-xl p-3 ${message.role === "user" ? "ml-auto bg-red-500/15 text-red-50" : "mr-auto bg-white/[0.06] text-slate-200"}`}>
                {message.role === "assistant" ? <MarkdownAnswer content={message.content} /> : <p className="whitespace-pre-wrap text-xs leading-5">{message.content}</p>}
                {message.role === "assistant" && <div className="mt-2 flex items-center justify-between border-t border-white/10 pt-2"><span className="text-[9px] text-slate-600">VidQuery</span><button type="button" onClick={() => void copyAnswer(message)} className="rounded-md px-2 py-1 text-[10px] text-slate-400 hover:bg-white/10 hover:text-white">{copiedMessageId === message.id ? "Copied" : "Copy answer"}</button></div>}
                {message.sources && message.sources.length > 0 && <details className="group mt-2 border-t border-white/10 pt-2"><summary className="flex cursor-pointer list-none items-center justify-between gap-2 rounded-lg py-1 text-[10px] font-semibold text-slate-400 transition hover:text-slate-200 [&::-webkit-details-marker]:hidden"><span>Sources ({message.sources.length})</span><span className="inline-block text-xs transition-transform duration-200 group-open:rotate-180">⌄</span></summary><div className="mt-2 space-y-2">{message.sources.map((source, index) => <a key={`${source.chunk_id ?? "source"}-${index}`} href={sourceUrl(source)} target="_blank" rel="noreferrer" className="block rounded-lg border border-white/5 bg-black/20 p-2 text-[11px] leading-4 text-sky-300 hover:border-sky-400/20 hover:bg-black/30"><span className="font-semibold">{source.start_time !== null ? formatTimestamp(source.start_time) : "Timestamp unavailable"}{source.end_time !== null ? ` – ${formatTimestamp(source.end_time)}` : ""}</span><span className="mt-1 block line-clamp-4 text-slate-400">{source.content}</span></a>)}</div></details>}
              </article>)}
              {asking && <div className="mr-auto flex items-center gap-2 rounded-xl bg-white/[0.06] px-3 py-2 text-xs text-slate-400"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-400" />VidQuery is responding...</div>}
              {chatError && <div role="alert" className="rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-[10px] leading-5 text-red-200"><p>{chatError}</p>{failedQuestion && !asking && <button type="button" onClick={() => void sendQuestion(failedQuestion, false)} className="mt-2 rounded-md bg-red-400/15 px-2.5 py-1.5 font-semibold text-red-100 hover:bg-red-400/25">Retry response</button>}</div>}
            </div>

            <form onSubmit={(event) => void handleAsk(event)} className="flex gap-2 border-t border-white/10 p-3"><input value={question} onChange={(event) => setQuestion(event.target.value)} disabled={!isIndexed || asking} placeholder={isIndexed ? "Ask about this video..." : "Index video to start chatting"} className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/20 px-3 py-3 text-xs text-white outline-none placeholder:text-slate-600 focus:border-red-400/50 disabled:opacity-50" />{asking ? <button type="button" onClick={stopGeneration} className="rounded-xl border border-white/15 px-3 text-xs font-semibold text-slate-200 hover:bg-white/10">Stop</button> : <button type="submit" disabled={!isIndexed || !question.trim()} className="rounded-xl bg-red-500 px-4 text-xs font-semibold text-white hover:bg-red-400 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-slate-500">Send</button>}</form>
          </section>
        )}
        {!sessionReady && video && <p className="text-center text-xs text-slate-500">Restoring saved chats...</p>}
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3"><p className="text-xs font-medium text-slate-300">Phase 6 · Live streaming chat</p><p className="mt-1 text-[10px] leading-5 text-slate-500">Token-by-token responses · Collapsible sources · Copy · Retry · Stop generation</p></div>
      </section>
    </main>
  );
}
