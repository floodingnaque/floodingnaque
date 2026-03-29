/** Chat API types - shared between hooks and components. */

export interface ChatMessage {
  id: string;
  barangay_id: string;
  user_id: number;
  user_name: string;
  user_role: "user" | "operator" | "admin";
  content: string;
  message_type: "text" | "alert" | "status_update" | "flood_report";
  report_id: number | null;
  is_pinned: boolean;
  created_at: string;
}

export interface ChatChannel {
  barangay_id: string;
  display_name: string;
}

export interface PresenceUser {
  user_id: number;
  user_name: string;
  user_role: string;
  online_at?: string;
}

export interface TypingPayload {
  user_name: string;
  user_id: number;
  user_role?: "user" | "operator" | "admin";
  is_typing: boolean;
}
