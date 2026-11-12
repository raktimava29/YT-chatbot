// Open VidQuery side panel when user clicks extension toolbar icon.
chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error("VIDQUERY: Failed to configure side panel", error));
});

// Reapply behavior when browser starts, including after service worker restarts.
chrome.runtime.onStartup.addListener(() => {
  chrome.sidePanel
    .setPanelBehavior({ openPanelOnActionClick: true })
    .catch((error) => console.error("VIDQUERY: Failed to configure side panel", error));
});
