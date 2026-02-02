/**
 * useAuth Hook
 *
 * Comprehensive authentication hook providing login, register,
 * logout mutations, profile queries, and auth state management.
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
  User,
  AuthTokens,
} from '@/types';

/**
 * Query keys for auth-related queries
 */
export const authQueryKeys = {
  all: ['auth'] as const,
  profile: () => [...authQueryKeys.all, 'profile'] as const,
};

/**
 * Transform TokenResponse to AuthTokens format used by the store
 */
function transformTokenResponse(response: {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}): AuthTokens {
  return {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    tokenType: response.token_type,
    expiresIn: response.expires_in,
  };
}

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
   */
  const loginMutation = useMutation({
    mutationFn: (credentials: LoginRequest) => authApi.login(credentials),
    onSuccess: async (data) => {
      const tokens = transformTokenResponse(data);
      // Fetch user profile after successful login
      const userProfile = await authApi.getMe();
      setAuth(userProfile, tokens);
      navigate('/');
    },
  });

  /**
   * Register mutation
   */
  const registerMutation = useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: async (data) => {
      const tokens = transformTokenResponse(data);
      // Fetch user profile after successful registration
      const userProfile = await authApi.getMe();
      setAuth(userProfile, tokens);
      navigate('/');
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
      // Update user in store
      const currentState = useAuthStore.getState();
      if (currentState.accessToken && currentState.refreshToken) {
        setAuth(updatedUser, {
          accessToken: currentState.accessToken,
          refreshToken: currentState.refreshToken,
          tokenType: 'Bearer',
          expiresIn: 3600,
        });
      }
      // Invalidate profile query to refetch
      queryClient.invalidateQueries({ queryKey: authQueryKeys.profile() });
    },
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
  };
}

export default useAuth;
