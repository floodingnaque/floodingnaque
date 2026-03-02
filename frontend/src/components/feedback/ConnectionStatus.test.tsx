/**
 * ConnectionStatus Component Tests
 *
 * Tests the SSE connection status indicator across all states:
 * connected, disconnected, error - plus size variants and showLabel prop.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConnectionStatus } from './ConnectionStatus';

// ---------------------------------------------------------------------------
// Mock alertStore – default state: disconnected, no error
// ---------------------------------------------------------------------------
const mockAlertStoreState = {
  isConnected: false,
  connectionError: null as string | null,
};

vi.mock('@/state/stores/alertStore', () => ({
  useAlertStore: vi.fn((selector?: (state: typeof mockAlertStoreState) => unknown) => {
    if (typeof selector === 'function') {
      return selector(mockAlertStoreState);
    }
    return mockAlertStoreState;
  }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function setStoreState(overrides: Partial<typeof mockAlertStoreState>) {
  Object.assign(mockAlertStoreState, overrides);
}

function resetStoreState() {
  mockAlertStoreState.isConnected = false;
  mockAlertStoreState.connectionError = null;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('ConnectionStatus', () => {
  beforeEach(() => {
    resetStoreState();
  });

  // ── Disconnected State (default) ────────────────────────────────────────
  describe('disconnected state', () => {
    it('renders "Disconnected" text when not connected', () => {
      render(<ConnectionStatus />);
      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });

    it('has role="status" for accessibility', () => {
      render(<ConnectionStatus />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has aria-live="polite"', () => {
      render(<ConnectionStatus />);
      expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
    });

    it('applies red border styling', () => {
      render(<ConnectionStatus />);
      const badge = screen.getByText('Disconnected').closest('[class*="border-red"]');
      expect(badge).toBeInTheDocument();
    });
  });

  // ── Connected State ─────────────────────────────────────────────────────
  describe('connected state', () => {
    beforeEach(() => {
      setStoreState({ isConnected: true });
    });

    it('renders "Connected" text', () => {
      render(<ConnectionStatus />);
      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('does not render "Disconnected"', () => {
      render(<ConnectionStatus />);
      expect(screen.queryByText('Disconnected')).not.toBeInTheDocument();
    });

    it('applies green border styling', () => {
      render(<ConnectionStatus />);
      const badge = screen.getByText('Connected').closest('[class*="border-green"]');
      expect(badge).toBeInTheDocument();
    });

    it('has role="status"', () => {
      render(<ConnectionStatus />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

  // ── Error State ─────────────────────────────────────────────────────────
  describe('error state', () => {
    const errorMessage = 'SSE connection timed out';

    beforeEach(() => {
      setStoreState({ isConnected: false, connectionError: errorMessage });
    });

    it('renders the error message', () => {
      render(<ConnectionStatus />);
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it('does not render "Connected" or "Disconnected"', () => {
      render(<ConnectionStatus />);
      expect(screen.queryByText('Connected')).not.toBeInTheDocument();
      expect(screen.queryByText('Disconnected')).not.toBeInTheDocument();
    });

    it('applies amber border styling', () => {
      render(<ConnectionStatus />);
      const badge = screen.getByText(errorMessage).closest('[class*="border-amber"]');
      expect(badge).toBeInTheDocument();
    });

    it('has role="status"', () => {
      render(<ConnectionStatus />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('error takes precedence over connected state', () => {
      setStoreState({ isConnected: true, connectionError: errorMessage });
      render(<ConnectionStatus />);
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(screen.queryByText('Connected')).not.toBeInTheDocument();
    });
  });

  // ── showLabel Prop ──────────────────────────────────────────────────────
  describe('showLabel prop', () => {
    it('shows label text by default', () => {
      render(<ConnectionStatus />);
      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });

    it('hides label text when showLabel is false (disconnected)', () => {
      render(<ConnectionStatus showLabel={false} />);
      expect(screen.queryByText('Disconnected')).not.toBeInTheDocument();
    });

    it('hides label text when showLabel is false (connected)', () => {
      setStoreState({ isConnected: true });
      render(<ConnectionStatus showLabel={false} />);
      expect(screen.queryByText('Connected')).not.toBeInTheDocument();
    });

    it('hides error text when showLabel is false (error)', () => {
      setStoreState({ connectionError: 'Network error' });
      render(<ConnectionStatus showLabel={false} />);
      expect(screen.queryByText('Network error')).not.toBeInTheDocument();
    });
  });

  // ── Size Variants ───────────────────────────────────────────────────────
  describe('size variants', () => {
    it('renders with sm size', () => {
      const { container } = render(<ConnectionStatus size="sm" />);
      const wrapper = container.querySelector('[class*="gap-1"]');
      expect(wrapper).toBeInTheDocument();
    });

    it('renders with md size (default)', () => {
      const { container } = render(<ConnectionStatus />);
      const wrapper = container.querySelector('[class*="gap-1"]');
      expect(wrapper).toBeInTheDocument();
    });

    it('renders with lg size', () => {
      const { container } = render(<ConnectionStatus size="lg" />);
      const wrapper = container.querySelector('[class*="gap-2"]');
      expect(wrapper).toBeInTheDocument();
    });
  });

  // ── Custom className ────────────────────────────────────────────────────
  describe('className prop', () => {
    it('applies custom className to wrapper', () => {
      const { container } = render(<ConnectionStatus className="my-custom-class" />);
      expect(container.querySelector('.my-custom-class')).toBeInTheDocument();
    });
  });
});
