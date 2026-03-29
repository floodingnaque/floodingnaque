/**
 * Tab Leader Election via BroadcastChannel
 *
 * Elects a single tab as "leader" to own the SSE connection.
 * Follower tabs receive alerts via the tab-sync BroadcastChannel.
 *
 * Algorithm:
 *  1. Each tab generates a unique ID (uuid())
 *  2. Tab claims leadership if no heartbeat is received within 3s
 *  3. Leader sends heartbeat every 2s
 *  4. On beforeunload, leader resigns
 *  5. Followers re-elect on missed heartbeat
 */

import { uuid } from "@/lib/uuid";

type LeaderMessage =
  | { type: "LEADER_HEARTBEAT"; tabId: string }
  | { type: "LEADER_CLAIM"; tabId: string; timestamp: number }
  | { type: "LEADER_RESIGN"; tabId: string };

const CHANNEL_NAME = "floodingnaque-leader";
const HEARTBEAT_INTERVAL_MS = 2_000;
const ELECTION_TIMEOUT_MS = 3_000;

let channel: BroadcastChannel | null = null;
let tabId: string = "";
let _isLeader = false;
let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let electionTimer: ReturnType<typeof setTimeout> | null = null;
let listeners: Array<(leader: boolean) => void> = [];

function notifyListeners(): void {
  for (const cb of listeners) cb(_isLeader);
}

function startHeartbeat(): void {
  stopHeartbeat();
  heartbeatTimer = setInterval(() => {
    channel?.postMessage({
      type: "LEADER_HEARTBEAT",
      tabId,
    } satisfies LeaderMessage);
  }, HEARTBEAT_INTERVAL_MS);
}

function stopHeartbeat(): void {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function resetElectionTimer(): void {
  if (electionTimer) clearTimeout(electionTimer);
  electionTimer = setTimeout(() => {
    // No heartbeat received - claim leadership
    claimLeadership();
  }, ELECTION_TIMEOUT_MS);
}

function claimLeadership(): void {
  _isLeader = true;
  channel?.postMessage({
    type: "LEADER_CLAIM",
    tabId,
    timestamp: Date.now(),
  } satisfies LeaderMessage);
  startHeartbeat();
  notifyListeners();
}

function resign(): void {
  if (_isLeader) {
    channel?.postMessage({
      type: "LEADER_RESIGN",
      tabId,
    } satisfies LeaderMessage);
    _isLeader = false;
    stopHeartbeat();
    notifyListeners();
  }
}

function handleMessage(event: MessageEvent<LeaderMessage>): void {
  const msg = event.data;

  switch (msg.type) {
    case "LEADER_HEARTBEAT":
    case "LEADER_CLAIM":
      if (msg.tabId !== tabId) {
        // Another tab is leader - become follower
        if (_isLeader) {
          _isLeader = false;
          stopHeartbeat();
          notifyListeners();
        }
        resetElectionTimer();
      }
      break;

    case "LEADER_RESIGN":
      if (msg.tabId !== tabId) {
        // Leader resigned - start election
        resetElectionTimer();
      }
      break;
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function isLeader(): boolean {
  return _isLeader;
}

export function onLeaderChange(cb: (isLeader: boolean) => void): () => void {
  listeners.push(cb);
  return () => {
    listeners = listeners.filter((l) => l !== cb);
  };
}

export function initLeaderElection(): () => void {
  if (typeof BroadcastChannel === "undefined") {
    // No BroadcastChannel support - this tab is always leader
    _isLeader = true;
    notifyListeners();
    return () => {};
  }

  tabId = uuid();
  channel = new BroadcastChannel(CHANNEL_NAME);
  channel.addEventListener("message", handleMessage);

  // Start election timeout - if no leader responds, we become leader
  resetElectionTimer();

  const handleUnload = () => resign();
  window.addEventListener("beforeunload", handleUnload);

  return () => {
    resign();
    if (electionTimer) clearTimeout(electionTimer);
    window.removeEventListener("beforeunload", handleUnload);
    channel?.removeEventListener("message", handleMessage);
    channel?.close();
    channel = null;
    listeners = [];
  };
}
