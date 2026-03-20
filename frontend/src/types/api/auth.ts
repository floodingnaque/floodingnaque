export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  full_name?: string;
}

/**
 * Extended registration request for LGU resident onboarding.
 * Captures detailed info for DRRM emergency management.
 */
export interface ResidentRegistrationRequest {
  // Step 1 — Account
  full_name: string;
  email: string;
  password: string;

  // Step 2 — Personal & Household
  date_of_birth: string;
  sex: "Male" | "Female" | "Prefer not to say";
  civil_status: "Single" | "Married" | "Widowed" | "Separated";
  contact_number: string;
  alt_contact_number?: string;
  alt_contact_name?: string;
  alt_contact_relationship?: string;
  is_pwd?: boolean;
  is_senior_citizen?: boolean;
  household_members: number;
  children_count?: number;
  senior_count?: number;
  pwd_count?: number;

  // Step 3 — Address & Location
  barangay: string;
  purok?: string;
  street_address: string;
  nearest_landmark?: string;
  home_type: "Concrete" | "Semi-Concrete" | "Wood" | "Makeshift";
  floor_level: "Ground Floor" | "2nd Floor" | "3rd Floor or higher";
  has_flood_experience?: boolean;
  most_recent_flood_year?: number;

  // Notification Preferences
  sms_alerts: boolean;
  email_alerts: boolean;
  push_notifications: boolean;
  preferred_language: "Filipino" | "English";

  // Consent
  data_privacy_consent: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
  expires_in: number;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  full_name?: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified?: boolean;
  avatarUrl?: string | null;
  created_at: string | null;
  updated_at?: string | null;
  last_login_at?: string | null;
}

export type UserRole = "user" | "admin" | "operator";

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface UpdateProfileRequest {
  name?: string;
  email?: string;
}

/**
 * Request a password reset email
 */
export interface PasswordResetRequest {
  email: string;
}

/**
 * Response from the password reset request endpoint.
 * In development mode (SMTP not configured), includes `dev_token`
 * so the reset flow can be tested without an email server.
 */
export interface PasswordResetResponse {
  success: boolean;
  message: string;
  /** Only present in development when SMTP is not configured */
  dev_token?: string;
  request_id?: string;
}

/**
 * Confirm a password reset with the emailed token
 */
export interface PasswordResetConfirmRequest {
  email: string;
  token: string;
  new_password: string;
}

/**
 * Auth tokens structure used by the auth store
 */
export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}
