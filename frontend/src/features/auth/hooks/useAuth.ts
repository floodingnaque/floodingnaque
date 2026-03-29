/**
 * useAuth Hook
 *
 * Comprehensive authentication hook providing login, register,
 * logout mutations, profile queries, and auth state management.
 * Access and refresh tokens are stored in memory and sent as
 * Authorization: Bearer headers.
 */

import { useAuthStore } from "@/state/stores/authStore";
import type {
  ChangePasswordRequest,
  LoginRequest,
  PasswordResetConfirmRequest,
  PasswordResetRequest,
  PasswordResetResponse,
  RegisterRequest,
  ResidentRegistrationRequest,
  UpdateProfileRequest,
  User,
} from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authApi } from "../services/authApi";

/**
 * Query keys for auth-related queries
 */
export const authQueryKeys = {
  all: ["auth"] as const,
  profile: () => [...authQueryKeys.all, "profile"] as const,
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
   * that carries `user` as a first-class field - no unsafe casts.
   */
  const loginMutation = useMutation({
    mutationFn: (credentials: LoginRequest) => authApi.login(credentials),
    onSuccess: (data) => {
      // Store user metadata and tokens in the auth store.
      // Tokens are kept in memory and attached via Authorization header.
      setAuth(
        data.user,
        data.csrf_token,
        data.access_token,
        data.refresh_token,
      );
      // Invalidate any stale profile/auth queries so UI reflects the new user
      queryClient.invalidateQueries({ queryKey: authQueryKeys.all });
    },
  });

  /**
   * Register mutation
   */
  const registerMutation = useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: (data) => {
      setAuth(
        data.user,
        data.csrf_token,
        data.access_token,
        data.refresh_token,
      );
      queryClient.invalidateQueries({ queryKey: authQueryKeys.all });
    },
  });

  /**
   * Register resident mutation (full onboarding wizard data)
   */
  const registerResidentMutation = useMutation({
    mutationFn: (data: ResidentRegistrationRequest) =>
      authApi.registerResident(data),
  });

  /**
   * Logout mutation
   */
  const logoutMutation = useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      clearAuth();
      queryClient.clear();
      navigate("/login");
    },
    onError: () => {
      // Even if logout fails on server, clear local auth state
      clearAuth();
      queryClient.clear();
      navigate("/login");
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
      // Update user in store - keep existing tokens
      setAuth(updatedUser);
      // Invalidate profile query to refetch
      queryClient.invalidateQueries({ queryKey: authQueryKeys.profile() });
    },
  });

  /**
   * Request password reset mutation
   */
  const requestPasswordResetMutation = useMutation<
    PasswordResetResponse,
    Error,
    PasswordResetRequest
  >({
    mutationFn: (data: PasswordResetRequest) =>
      authApi.requestPasswordReset(data),
  });

  /**
   * Confirm password reset mutation
   */
  const confirmPasswordResetMutation = useMutation({
    mutationFn: (data: PasswordResetConfirmRequest) =>
      authApi.confirmPasswordReset(data),
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

    // Register resident (full wizard)
    registerResident: registerResidentMutation.mutate,
    isRegisteringResident: registerResidentMutation.isPending,
    registerResidentError: registerResidentMutation.error,

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
