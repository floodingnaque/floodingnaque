/**
 * Utility Functions
 *
 * Shared utility helpers used across the frontend application.
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge and deduplicate Tailwind CSS class names.
 *
 * Combines `clsx` (conditional classes) with `tailwind-merge`
 * (intelligent deduplication of conflicting Tailwind utilities).
 *
 * @example
 * cn('px-4 py-2', condition && 'bg-red-500', 'px-6')
 * // → 'py-2 px-6 bg-red-500'   (px-4 correctly overridden by px-6)
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Truncate a string to a maximum length and append an ellipsis.
 *
 * @param str  - The string to truncate
 * @param max  - Maximum character length (default: 50)
 * @returns The truncated string, or the original if already short enough
 */
export function truncate(str: string, max = 50): string {
  if (str.length <= max) return str;
  return `${str.slice(0, max)}…`;
}

/**
 * Format an ISO date string to a human-readable relative time.
 *
 * @param dateString - ISO 8601 date string
 * @returns A relative time string like "2 hours ago" or "just now"
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 30) return `${diffDay}d ago`;
  const diffMonth = Math.floor(diffDay / 30);
  if (diffMonth < 12) return `${diffMonth}mo ago`;
  const diffYear = Math.floor(diffMonth / 12);
  return `${diffYear}y ago`;
}
