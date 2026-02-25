/**
 * ClassName Utility
 * 
 * Combines clsx and tailwind-merge for conditional class names
 * with proper Tailwind CSS class conflict resolution.
 */

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Combines class names using clsx and resolves Tailwind conflicts with twMerge.
 * 
 * @param inputs - Class values to combine (strings, arrays, objects, etc.)
 * @returns Merged class string with Tailwind conflicts resolved
 * 
 * @example
 * cn('px-2 py-1', 'px-4') // => 'py-1 px-4'
 * cn('text-red-500', condition && 'text-blue-500') // conditionally applies classes
 * cn({ 'bg-primary': isActive }, 'hover:bg-secondary') // object syntax
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
