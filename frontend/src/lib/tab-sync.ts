/**
 * Cross-Tab Synchronization via BroadcastChannel
 *
 * Syncs alerts, risk level changes, and auth events across browser tabs.
 * Uses a flag to prevent infinite loops when receiving messages.
 */

import type { Alert } from "@/types";

// ---------------------------------------------------------------------------
// Message protocol
// ---------------------------------------------------------------------------

type TabSyncMessage =
  | { type: "NEW_ALERT"; payload: Alert }
  | { type: "RISK_LEVEL_CHANGE"; payload: string }
  | { type: "AUTH_LOGOUT" }
  | { type: "TOKEN_REFRESH"; payload: string };

// ---------------------------------------------------------------------------
// Channel singleton
// ---------------------------------------------------------------------------

const CHANNEL_NAME = "floodingnaque-sync";

let channel: BroadcastChannel | null = null;

function getChannel(): BroadcastChannel | null {
  if (typeof BroadcastChannel === "undefined") return null;
  if (!channel) {
    channel = new BroadcastChannel(CHANNEL_NAME);
  }
  return channel;
}

// ---------------------------------------------------------------------------
// Post helpers (called from stores)
// ---------------------------------------------------------------------------

export function postTabMessage(message: TabSyncMessage): void {
  getChannel()?.postMessage(message);
}

// ---------------------------------------------------------------------------
// Init — wire up listeners
// ---------------------------------------------------------------------------

type StoreRefs = {
  addAlertSilent: (alert: Alert) => void;
  clearAuthSilent: () => void;
  setAccessTokenSilent: (token: string) => void;
};

let cleanup: (() => void) | null = null;

export function initTabSync(stores: StoreRefs): () => void {
  const ch = getChannel();
  if (!ch) return () => {};

  const handler = (event: MessageEvent<TabSyncMessage>) => {
    const msg = event.data;
    switch (msg.type) {
      case "NEW_ALERT":
        stores.addAlertSilent(msg.payload);
        break;
      case "AUTH_LOGOUT":
        stores.clearAuthSilent();
        break;
      case "TOKEN_REFRESH":
        stores.setAccessTokenSilent(msg.payload);
        break;
    }
  };

  ch.addEventListener("message", handler);

  cleanup = () => {
    ch.removeEventListener("message", handler);
    ch.close();
    channel = null;
  };

  return cleanup;
}

export function cleanupTabSync(): void {
  cleanup?.();
}
