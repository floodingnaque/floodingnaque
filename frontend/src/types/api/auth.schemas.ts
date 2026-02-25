/**
 * Zod Schemas for Auth API Responses
 *
 * Runtime validation schemas that replace unsafe `as unknown as` casts.
 * Each schema mirrors the corresponding TypeScript interface in ./auth.ts.
 */

import { z } from 'zod';

// ---------------------------------------------------------------------------
// User
// ---------------------------------------------------------------------------

export const UserSchema = z.object({
  id: z.number(),
  email: z.string(),
  name: z.string(),
  full_name: z.string().nullable().optional(),
  role: z.enum(['user', 'admin', 'operator']),
  is_active: z.boolean(),
  is_verified: z.boolean().optional(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable().optional(),
  last_login_at: z.string().nullable().optional(),
});

// ---------------------------------------------------------------------------
// Login / Register response
// ---------------------------------------------------------------------------

/**
 * The server returns token fields alongside an embedded `user` object.
 * This schema validates the full login / register response before the
 * caller destructures it.
 */
export const AuthResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
  expires_in: z.number(),
  user: UserSchema,
  /** CSRF token returned when using httpOnly cookie auth */
  csrf_token: z.string().optional(),
});

// ---------------------------------------------------------------------------
// GET /auth/me response
// ---------------------------------------------------------------------------

export const MeResponseSchema = z.object({
  success: z.boolean(),
  user: UserSchema,
});

// ---------------------------------------------------------------------------
// Inferred types (for convenience)
// ---------------------------------------------------------------------------

export type AuthResponse = z.infer<typeof AuthResponseSchema>;
export type MeResponse = z.infer<typeof MeResponseSchema>;
