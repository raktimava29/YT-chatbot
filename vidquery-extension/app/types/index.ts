import type { ChatSource } from "../lib/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  createdAt: number;
}

export interface ChatSession {
  id: string;
  videoId: string;
  videoTitle: string;
  thumbnailUrl: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
}
