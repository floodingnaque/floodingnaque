/**
 * useAuth Hook
 *
 * Comprehensive authentication hook providing login, register,
 * logout mutations, profile queries, and auth state management.
 * Auth tokens are stored in httpOnly cookies — the store only
 * tracks user metadata and a CSRF token.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/state/stores/authStore';
import { authApi } from '../services/authApi';
import type {
  LoginRequest,
  RegisterRequest,
  ChangePasswordRequest,
  UpdateProfileRequest,
  PasswordResetRequest,
  PasswordResetConfirmRequest,
  User,
} from '@/types';

/**
 * Query keys for auth-related queries
 */
export const authQueryKeys = {
  all: ['auth'] as const,
  profile: () => [...authQueryKeys.all, 'profile'] as const,
};

/**
 * useAuth hook for authentication management
 */
export function useAuth() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Auth store state and actions
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const setAuth = useAuthStore((state) => state.setAuth);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  /**
   * Login mutation
   *
   * `authApi.login` now returns a Zod-validated `AuthResponse`
   * that carries `user` as a first-class field — no unsafe casts.
   */
  const loginMutation = useMutation({
    mutationFn: (credentials: LoginRequest) => authApi.login(credentials),
    onSuccess: (data) => {
      // Tokens are set as httpOnly cookies by the server.
      // We only persist the user + optional CSRF token.
      setAuth(data.user, data.csrf_token);
    },
  });

  /**
   * Register mutation
   */
  const registerMutation = useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: (data) => {
      setAuth(data.user, data.csrf_token);
    },
  });

  /**
   * Logout mutation
   */
  const logoutMutation = useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      clearAuth();
      queryClient.invalidateQueries();
      navigate('/login');
    },
    onError: () => {
      // Even if logout fails on server, clear local auth state
      clearAuth();
      queryClient.invalidateQueries();
      navigate('/login');
    },
  });

  /**
   * Profile query - fetch current user data
   */
  const profileQuery = useQuery({
    queryKey: authQueryKeys.profile(),
    queryFn: () => authApi.getMe(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });

  /**
   * Change password mutation
   */
  const changePasswordMutation = useMutation({
    mutationFn: (data: ChangePasswordRequest) => authApi.changePassword(data),
  });

  /**
   * Update profile mutation
   */
  const updateProfileMutation = useMutation({
    mutationFn: (data: UpdateProfileRequest) => authApi.updateProfile(data),
    onSuccess: (updatedUser: User) => {
      // Update user in store — tokens remain in httpOnly cookies
      setAuth(updatedUser);
      // Invalidate profile query to refetch
      queryClient.invalidateQueries({ queryKey: authQueryKeys.profile() });
    },
  });

  /**
   * Request password reset mutation
   */
  const requestPasswordResetMutation = useMutation({
    mutationFn: (data: PasswordResetRequest) => authApi.requestPasswordReset(data),
  });

  /**
   * Confirm password reset mutation
   */
  const confirmPasswordResetMutation = useMutation({
    mutationFn: (data: PasswordResetConfirmRequest) => authApi.confirmPasswordReset(data),
  });

  return {
    // State
    user,
    isAuthenticated,

    // Login
    login: loginMutation.mutate,
    loginAsync: loginMutation.mutateAsync,
    isLoggingIn: loginMutation.isPending,
    loginError: loginMutation.error,

    // Register
    register: registerMutation.mutate,
    registerAsync: registerMutation.mutateAsync,
    isRegistering: registerMutation.isPending,
    registerError: registerMutation.error,

    // Logout
    logout: logoutMutation.mutate,
    logoutAsync: logoutMutation.mutateAsync,
    isLoggingOut: logoutMutation.isPending,

    // Profile
    profileQuery,

    // Change password
    changePassword: changePasswordMutation.mutate,
    changePasswordAsync: changePasswordMutation.mutateAsync,
    isChangingPassword: changePasswordMutation.isPending,
    changePasswordError: changePasswordMutation.error,

    // Update profile
    updateProfile: updateProfileMutation.mutate,
    updateProfileAsync: updateProfileMutation.mutateAsync,
    isUpdatingProfile: updateProfileMutation.isPending,
    updateProfileError: updateProfileMutation.error,

    // Password reset
    requestPasswordReset: requestPasswordResetMutation.mutate,
    isRequestingPasswordReset: requestPasswordResetMutation.isPending,
    requestPasswordResetError: requestPasswordResetMutation.error,

    confirmPasswordReset: confirmPasswordResetMutation.mutate,
    isConfirmingPasswordReset: confirmPasswordResetMutation.isPending,
    confirmPasswordResetError: confirmPasswordResetMutation.error,
  };
}

export default useAuth;