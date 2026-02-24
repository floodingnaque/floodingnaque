export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
  expires_in: number;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export type UserRole = 'user' | 'admin';

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
