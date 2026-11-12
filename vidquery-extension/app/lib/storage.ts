import type { ChatSession } from "../types";

const SESSIONS_KEY = "vidquery.sessions.v1";
const SELECTED_KEY = "vidquery.selectedSessions.v1";
const INDEXED_KEY = "vidquery.indexedVideos.v1";

export async function getSessions(): Promise<ChatSession[]> {
  const result = await chrome.storage.local.get(SESSIONS_KEY);
  const sessions = result[SESSIONS_KEY];
  return Array.isArray(sessions) ? (sessions as ChatSession[]) : [];
}

export async function saveSession(session: ChatSession): Promise<void> {
  const sessions = await getSessions();
  const index = sessions.findIndex((item) => item.id === session.id);
  if (index >= 0) sessions[index] = session;
  else sessions.push(session);
  await chrome.storage.local.set({ [SESSIONS_KEY]: sessions });
}

export async function removeSession(sessionId: string): Promise<void> {
  const sessions = (await getSessions()).filter((item) => item.id !== sessionId);
  const selected = await getSelectedSessions();
  for (const [videoId, id] of Object.entries(selected)) {
    if (id === sessionId) delete selected[videoId];
  }
  await chrome.storage.local.set({
    [SESSIONS_KEY]: sessions,
    [SELECTED_KEY]: selected,
  });
}

export async function getSelectedSessions(): Promise<Record<string, string>> {
  const result = await chrome.storage.local.get(SELECTED_KEY);
  const value = result[SELECTED_KEY];
  return value && typeof value === "object" ? (value as Record<string, string>) : {};
}

export async function setSelectedSession(videoId: string, sessionId: string): Promise<void> {
  const selected = await getSelectedSessions();
  selected[videoId] = sessionId;
  await chrome.storage.local.set({ [SELECTED_KEY]: selected });
}

export async function getIndexedVideos(): Promise<string[]> {
  const result = await chrome.storage.local.get(INDEXED_KEY);
  const value = result[INDEXED_KEY];
  return Array.isArray(value) ? (value as string[]) : [];
}

export async function markVideoIndexed(videoId: string): Promise<void> {
  const indexed = await getIndexedVideos();
  if (!indexed.includes(videoId)) indexed.push(videoId);
  await chrome.storage.local.set({ [INDEXED_KEY]: indexed });
}
