/**
 * AlertCard Component Tests
 *
 * Tests for the AlertCard component displaying individual alerts.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/utils';
import { AlertCard } from '@/features/alerts/components/AlertCard';
import type { Alert } from '@/types';

// Mock date-fns to have consistent time output
vi.mock('date-fns', async () => {
  const actual = await vi.importActual('date-fns');
  return {
    ...actual,
    formatDistanceToNow: () => '2 hours ago',
  };
});

describe('AlertCard', () => {
  const mockAlert: Alert = {
    id: 1,
    risk_level: 1,
    message: 'Flood warning for downtown area',
    location: 'Manila, Philippines',
    latitude: 14.5995,
    longitude: 120.9842,
    triggered_at: '2026-01-15T10:30:00Z',
    expires_at: '2026-01-16T10:30:00Z',
    acknowledged: false,
    created_at: '2026-01-15T10:30:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render alert message', () => {
      render(<AlertCard alert={mockAlert} />);

      expect(screen.getByText('Flood warning for downtown area')).toBeInTheDocument();
    });

    it('should render alert location', () => {
      render(<AlertCard alert={mockAlert} />);

      expect(screen.getByText('Manila, Philippines')).toBeInTheDocument();
    });

    it('should render relative time', () => {
      render(<AlertCard alert={mockAlert} />);

      expect(screen.getByText('2 hours ago')).toBeInTheDocument();
    });

    it('should render risk badge', () => {
      render(<AlertCard alert={{ ...mockAlert, risk_level: 2 }} />);

      expect(screen.getByText('Critical')).toBeInTheDocument();
    });

    it('should render acknowledge button for unacknowledged alerts', () => {
      render(<AlertCard alert={mockAlert} />);

      expect(screen.getByRole('button', { name: /acknowledge/i })).toBeInTheDocument();
    });

    it('should render acknowledged status for acknowledged alerts', () => {
      const acknowledgedAlert = { ...mockAlert, acknowledged: true };
      render(<AlertCard alert={acknowledgedAlert} />);

      expect(screen.getByText('Acknowledged')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /acknowledge/i })).not.toBeInTheDocument();
    });

    it('should not render location if not provided', () => {
      const alertWithoutLocation = { ...mockAlert, location: undefined };
      render(<AlertCard alert={alertWithoutLocation} />);

      expect(screen.queryByText('Manila, Philippines')).not.toBeInTheDocument();
    });
  });

  describe('Risk Level Display', () => {
    it('should display Safe badge for risk level 0', () => {
      render(<AlertCard alert={{ ...mockAlert, risk_level: 0 }} />);

      expect(screen.getByText('Safe')).toBeInTheDocument();
    });

    it('should display Alert badge for risk level 1', () => {
      render(<AlertCard alert={{ ...mockAlert, risk_level: 1 }} />);

      expect(screen.getByText('Alert')).toBeInTheDocument();
    });

    it('should display Critical badge for risk level 2', () => {
      render(<AlertCard alert={{ ...mockAlert, risk_level: 2 }} />);

      expect(screen.getByText('Critical')).toBeInTheDocument();
    });
  });

  describe('Acknowledge Action', () => {
    it('should call onAcknowledge when button is clicked', async () => {
      const onAcknowledge = vi.fn();
      const { user } = render(
        <AlertCard alert={mockAlert} onAcknowledge={onAcknowledge} />
      );

      await user.click(screen.getByRole('button', { name: /acknowledge/i }));

      expect(onAcknowledge).toHaveBeenCalledWith(mockAlert.id);
    });

    it('should not call onAcknowledge for acknowledged alerts', async () => {
      const onAcknowledge = vi.fn();
      const acknowledgedAlert = { ...mockAlert, acknowledged: true };
      render(<AlertCard alert={acknowledgedAlert} onAcknowledge={onAcknowledge} />);

      // No button should be present
      expect(screen.queryByRole('button', { name: /acknowledge/i })).not.toBeInTheDocument();
    });

    it('should show loading state when isAcknowledging is true', () => {
      render(<AlertCard alert={mockAlert} isAcknowledging />);

      expect(screen.getByRole('button', { name: /acknowledging/i })).toBeInTheDocument();
      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('should disable button during acknowledgment', () => {
      render(<AlertCard alert={mockAlert} isAcknowledging />);

      expect(screen.getByRole('button')).toBeDisabled();
    });
  });

  describe('Variants', () => {
    it('should render compact variant', () => {
      render(<AlertCard alert={mockAlert} compact />);

      expect(screen.getByText('Flood warning for downtown area')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const { container } = render(
        <AlertCard alert={mockAlert} className="custom-class" />
      );

      // The className is applied to the Card component which is the first child
      expect(container.firstChild).toHaveClass('custom-class');
    });
  });

  describe('Styling', () => {
    it('should have reduced opacity when acknowledged', () => {
      const { container } = render(
        <AlertCard alert={{ ...mockAlert, acknowledged: true }} />
      );

      // The opacity class is applied to the Card component which is the first child
      expect(container.firstChild).toHaveClass('opacity-60');
    });

    it('should have hover effect when not compact', () => {
      const { container } = render(<AlertCard alert={mockAlert} />);

      // The hover class is applied to the Card component which is the first child
      expect(container.firstChild).toHaveClass('hover:shadow-lg');
    });
  });
});

describe('AlertCard Accessibility', () => {
  const mockAlert: Alert = {
    id: 1,
    risk_level: 1,
    message: 'Flood warning',
    triggered_at: '2026-01-15T10:30:00Z',
    acknowledged: false,
    created_at: '2026-01-15T10:30:00Z',
  };

  it('should have accessible button', () => {
    render(<AlertCard alert={mockAlert} onAcknowledge={() => {}} />);

    const button = screen.getByRole('button', { name: /acknowledge/i });
    expect(button).toBeVisible();
  });
});
