/**
 * Authentication API Service
 *
 * Provides all authentication-related API calls including
 * login, register, token refresh, and profile management.
 */

import api from '@/lib/api-client';
import { API_CONFIG } from '@/config/api.config';
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  User,
  RefreshTokenRequest,
  ChangePasswordRequest,
  UpdateProfileRequest,
} from '@/types';

const { endpoints } = API_CONFIG;

/**
 * Authentication API methods
 */
export const authApi = {
  /**
   * Login with email and password
   */
  login: async (credentials: LoginRequest): Promise<TokenResponse> => {
    return api.post<TokenResponse>(endpoints.auth.login, credentials);
  },

  /**
   * Register a new user account
   */
  register: async (data: RegisterRequest): Promise<TokenResponse> => {
    return api.post<TokenResponse>(endpoints.auth.register, data);
  },

  /**
   * Refresh the access token using a refresh token
   */
  refresh: async (data: RefreshTokenRequest): Promise<TokenResponse> => {
    return api.post<TokenResponse>(endpoints.auth.refresh, data);
  },

  /**
   * Logout the current user (invalidate tokens on server)
   */
  logout: async (): Promise<void> => {
    return api.post<void>(endpoints.auth.logout);
  },

  /**
   * Get the current authenticated user's profile.
   * The backend returns { success, user } — we unwrap to a flat User here
   * so every consumer receives the correct shape with role intact.
   */
  getMe: async (): Promise<User> => {
    const response = await api.get<{ success: boolean; user: User }>(endpoints.auth.me);
    return (response as unknown as { user: User }).user ?? response;
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
    return api.patch<User>(endpoints.auth.me, data);
  },
};

export default authApi;