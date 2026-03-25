/**
 * Authentication API Service
 *
 * Provides all authentication-related API calls including
 * login, register, token refresh, and profile management.
 * Responses are validated at runtime with Zod schemas.
 */

import { API_CONFIG } from "@/config/api.config";
import api from "@/lib/api-client";
import type {
  ChangePasswordRequest,
  LoginRequest,
  PasswordResetConfirmRequest,
  PasswordResetRequest,
  PasswordResetResponse,
  RefreshTokenRequest,
  RegisterRequest,
  ResidentRegistrationRequest,
  UpdateProfileRequest,
  User,
} from "@/types";
import {
  AuthResponseSchema,
  MeResponseSchema,
  type AuthResponse,
} from "@/types/api/auth.schemas";

const { endpoints } = API_CONFIG;

/**
 * Authentication API methods
 */
export const authApi = {
  /**
   * Login with email and password.
   * The response is validated against AuthResponseSchema at runtime.
   */
  login: async (credentials: LoginRequest): Promise<AuthResponse> => {
    const raw = await api.post<unknown>(endpoints.auth.login, credentials);
    return AuthResponseSchema.parse(raw);
  },

  /**
   * Register a new user account.
   * The response is validated against AuthResponseSchema at runtime.
   */
  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const raw = await api.post<unknown>(endpoints.auth.register, data);
    return AuthResponseSchema.parse(raw);
  },

  /**
   * Register a resident with full onboarding data (all wizard steps).
   */
  registerResident: async (
    data: ResidentRegistrationRequest,
  ): Promise<AuthResponse> => {
    const raw = await api.post<unknown>(endpoints.auth.register, data);
    return AuthResponseSchema.parse(raw);
  },

  /**
   * Refresh the access token using a refresh token
   */
  refresh: async (data: RefreshTokenRequest): Promise<AuthResponse> => {
    const raw = await api.post<unknown>(endpoints.auth.refresh, data);
    return AuthResponseSchema.parse(raw);
  },

  /**
   * Logout the current user (invalidate tokens on server)
   */
  logout: async (): Promise<void> => {
    return api.post<void>(endpoints.auth.logout);
  },

  /**
   * Get the current authenticated user's profile.
   * The response is validated against MeResponseSchema at runtime,
   * eliminating the previous unsafe double-cast.
   */
  getMe: async (): Promise<User> => {
    const raw = await api.get<unknown>(endpoints.auth.me);
    const parsed = MeResponseSchema.parse(raw);
    return parsed.user;
  },

  /**
   * Change the current user's password
   */
  changePassword: async (data: ChangePasswordRequest): Promise<void> => {
    return api.post<void>(`${endpoints.auth.me}/change-password`, data);
  },

  /**
   * Update the current user's profile
   */
  updateProfile: async (data: UpdateProfileRequest): Promise<User> => {
    const raw = await api.patch<unknown>(endpoints.auth.me, data);
    const parsed = MeResponseSchema.parse(raw);
    return parsed.user;
  },

  /**
   * Request a password reset token (sent via email).
   * Always returns success to prevent email enumeration.
   * In dev mode (SMTP not configured), response may include `dev_token`.
   */
  requestPasswordReset: async (
    data: PasswordResetRequest,
  ): Promise<PasswordResetResponse> => {
    return api.post<PasswordResetResponse>(
      endpoints.auth.passwordResetRequest,
      data,
    );
  },

  /**
   * Confirm a password reset using the emailed token
   */
  confirmPasswordReset: async (
    data: PasswordResetConfirmRequest,
  ): Promise<void> => {
    return api.post<void>(endpoints.auth.passwordResetConfirm, data);
  },
};

export default authApi;
