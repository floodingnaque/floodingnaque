/**
 * Role-Based Route Configuration
 *
 * Single source of truth for role → default-route mapping.
 * Every redirect in the application must derive from this file.
 *
 * Note: The backend role for residents is "user", not "resident".
 */

import type { UserRole } from "@/types/api/auth";

/**
 * Default landing route for each role after login.
 */
export const ROLE_DEFAULT_ROUTES: Record<UserRole, string> = {
  user: "/resident",
  operator: "/operator",
  admin: "/admin",
} as const;

/**
 * Returns the default dashboard route for a given role.
 * Falls back to /login for unknown/missing roles.
 */
export function getDefaultRoute(role: string | undefined | null): string {
  if (!role) return "/login";
  return ROLE_DEFAULT_ROUTES[role as UserRole] ?? "/resident";
}

/**
 * Sub-routes each role owns - used for access-control checks.
 * Admin can access everything (handled in canAccessRoute).
 */
export const ROLE_OWNED_ROUTES: Record<UserRole, string[]> = {
  user: [
    "/resident",
    "/dashboard",
    "/predict",
    "/map",
    "/alerts",
    "/history",
    "/reports",
    "/settings",
    "/community",
    "/evacuation",
  ],
  operator: [
    "/operator",
    "/dashboard",
    "/predict",
    "/map",
    "/alerts",
    "/history",
    "/reports",
    "/analytics",
    "/settings",
    "/compliance",
    "/incidents",
    "/community",
    "/evacuation",
  ],
  admin: [
    "/admin",
    "/dashboard",
    "/predict",
    "/map",
    "/alerts",
    "/history",
    "/reports",
    "/analytics",
    "/settings",
    "/compliance",
    "/incidents",
    "/community",
    "/evacuation",
    "/operator",
    "/resident",
  ],
};

/**
 * Returns true if a role is allowed to access a given path.
 * Admin can access everything.
 */
export function canAccessRoute(role: string, path: string): boolean {
  if (role === "admin") return true;
  const owned = ROLE_OWNED_ROUTES[role as UserRole] ?? [];
  return owned.some((r) => path === r || path.startsWith(r + "/"));
}
