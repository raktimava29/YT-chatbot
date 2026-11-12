"use client";

import { useCallback, useEffect, useState } from "react";
import { buildYouTubeVideo, type YouTubeVideo } from "../lib/youtube";

type DetectionState = "loading" | "detected" | "unsupported" | "unavailable";

interface ActiveVideoState {
  video: YouTubeVideo | null;
  status: DetectionState;
  error: string | null;
}

export function useActiveYouTubeVideo() {
  const [state, setState] = useState<ActiveVideoState>({
    video: null,
    status: "loading",
    error: null,
  });

  const detectActiveTab = useCallback(async () => {
    if (typeof chrome === "undefined" || !chrome.tabs?.query) {
      setState({ video: null, status: "unavailable", error: "VidQuery must run inside Chrome or Brave extension side panel." });
      return;
    }

    try {
      const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
      const video = tab ? buildYouTubeVideo(tab) : null;
      setState({ video, status: video ? "detected" : "unsupported", error: null });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not inspect active browser tab.";
      setState({ video: null, status: "unavailable", error: message });
    }
  }, []);

  useEffect(() => {
    void detectActiveTab();

    if (typeof chrome === "undefined" || !chrome.tabs) return;

    const onActivated = () => void detectActiveTab();
    // Derive listener signature from installed @types/chrome definitions.
    type UpdatedListener = Parameters<typeof chrome.tabs.onUpdated.addListener>[0];
    const onUpdated: UpdatedListener = (_tabId, changeInfo, tab) => {
      if (tab.active && (changeInfo.url || changeInfo.title || changeInfo.status === "complete")) {
        void detectActiveTab();
      }
    };
    const onRemoved = () => void detectActiveTab();
    const onWindowFocusChanged = () => void detectActiveTab();

    chrome.tabs.onActivated.addListener(onActivated);
    chrome.tabs.onUpdated.addListener(onUpdated);
    chrome.tabs.onRemoved.addListener(onRemoved);
    chrome.windows.onFocusChanged.addListener(onWindowFocusChanged);

    return () => {
      chrome.tabs.onActivated.removeListener(onActivated);
      chrome.tabs.onUpdated.removeListener(onUpdated);
      chrome.tabs.onRemoved.removeListener(onRemoved);
      chrome.windows.onFocusChanged.removeListener(onWindowFocusChanged);
    };
  }, [detectActiveTab]);

  return { ...state, refresh: detectActiveTab };
}
