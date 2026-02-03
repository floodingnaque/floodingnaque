/**
 * Vitest Test Setup
 *
 * Global test setup including Jest DOM matchers and MSW server.
 */

import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { server } from '@/tests/mocks/server';

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock ResizeObserver
globalThis.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
})) as unknown as typeof ResizeObserver;

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

// Mock HTML5 Constraint Validation API to allow form libraries (react-hook-form/zod) to handle validation
// jsdom's native validation can interfere with form submission in tests
// Use Object.defineProperty to properly override the prototype methods and validity state
Object.defineProperty(HTMLInputElement.prototype, 'checkValidity', {
  configurable: true,
  value: vi.fn(() => true),
});
Object.defineProperty(HTMLInputElement.prototype, 'reportValidity', {
  configurable: true,
  value: vi.fn(() => true),
});
Object.defineProperty(HTMLInputElement.prototype, 'setCustomValidity', {
  configurable: true,
  value: vi.fn(),
});
Object.defineProperty(HTMLFormElement.prototype, 'checkValidity', {
  configurable: true,
  value: vi.fn(() => true),
});
Object.defineProperty(HTMLFormElement.prototype, 'reportValidity', {
  configurable: true,
  value: vi.fn(() => true),
});

// Also mock the validity property to always show valid state
const mockValidity: ValidityState = {
  badInput: false,
  customError: false,
  patternMismatch: false,
  rangeOverflow: false,
  rangeUnderflow: false,
  stepMismatch: false,
  tooLong: false,
  tooShort: false,
  typeMismatch: false,
  valid: true,
  valueMissing: false,
};
Object.defineProperty(HTMLInputElement.prototype, 'validity', {
  configurable: true,
  get: () => mockValidity,
});

// Mock URL.createObjectURL
globalThis.URL.createObjectURL = vi.fn(() => 'mock-url');
globalThis.URL.revokeObjectURL = vi.fn();

// Setup MSW server
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'warn' });
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
