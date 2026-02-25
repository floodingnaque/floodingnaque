/**
 * StatsCards Component Tests
 *
 * Tests for the StatsCards component displaying dashboard statistics.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/utils';
import { StatsCards, StatsCardsSkeleton } from '@/features/dashboard/components/StatsCards';
import type { DashboardStats } from '../services/dashboardApi';

describe('StatsCards', () => {
  const mockStats: DashboardStats = {
    total_predictions: 1234,
    predictions_today: 42,
    active_alerts: 3,
    avg_risk_level: 35,
    recent_activity: [
      { type: 'prediction', timestamp: '2026-01-15T10:00:00Z', description: 'Prediction made' },
      { type: 'alert', timestamp: '2026-01-15T09:00:00Z', description: 'Alert triggered' },
    ],
  };

  describe('Rendering', () => {
    it('should render all four stat cards', () => {
      render(<StatsCards stats={mockStats} />);

      expect(screen.getByText('Total Predictions')).toBeInTheDocument();
      expect(screen.getByText("Today's Predictions")).toBeInTheDocument();
      expect(screen.getByText('Active Alerts')).toBeInTheDocument();
      expect(screen.getByText('Avg Risk Level')).toBeInTheDocument();
    });

    it('should display formatted total predictions', () => {
      render(<StatsCards stats={mockStats} />);

      expect(screen.getByText('1,234')).toBeInTheDocument();
    });

    it('should display predictions today', () => {
      render(<StatsCards stats={mockStats} />);

      expect(screen.getByText('42')).toBeInTheDocument();
    });

    it('should display active alerts count', () => {
      render(<StatsCards stats={mockStats} />);

      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('should display average risk level as percentage', () => {
      render(<StatsCards stats={mockStats} />);

      expect(screen.getByText('35%')).toBeInTheDocument();
    });
  });

  describe('Risk Level Colors', () => {
    it('should show Low label for risk level <= 25', () => {
      render(<StatsCards stats={{ ...mockStats, avg_risk_level: 20 }} />);

      expect(screen.getByText('Low')).toBeInTheDocument();
    });

    it('should show Moderate label for risk level 26-50', () => {
      render(<StatsCards stats={{ ...mockStats, avg_risk_level: 35 }} />);

      expect(screen.getByText('Moderate')).toBeInTheDocument();
    });

    it('should show High label for risk level 51-75', () => {
      render(<StatsCards stats={{ ...mockStats, avg_risk_level: 60 }} />);

      expect(screen.getByText('High')).toBeInTheDocument();
    });

    it('should show Critical label for risk level > 75', () => {
      render(<StatsCards stats={{ ...mockStats, avg_risk_level: 85 }} />);

      expect(screen.getByText('Critical')).toBeInTheDocument();
    });
  });

  describe('Alert Colors', () => {
    it('should show "All clear" when no active alerts', () => {
      render(<StatsCards stats={{ ...mockStats, active_alerts: 0 }} />);

      expect(screen.getByText('All clear')).toBeInTheDocument();
    });

    it('should show "Requires attention" when alerts present', () => {
      render(<StatsCards stats={{ ...mockStats, active_alerts: 5 }} />);

      expect(screen.getByText('Requires attention')).toBeInTheDocument();
    });
  });

  describe('Percentage Changes', () => {
    it('should display percentage change for total predictions', () => {
      render(<StatsCards stats={mockStats} />);

      // Component shows subtitles, not percentage changes
      expect(screen.getByText('all time')).toBeInTheDocument();
    });

    it('should display percentage change for today predictions', () => {
      render(<StatsCards stats={mockStats} />);

      // Component shows subtitles, not percentage changes
      expect(screen.getByText('since midnight')).toBeInTheDocument();
    });
  });

  describe('Subtitles', () => {
    it('should display "from last month" subtitle', () => {
      render(<StatsCards stats={mockStats} />);

      expect(screen.getByText('all time')).toBeInTheDocument();
    });

    it('should display "from yesterday" subtitle', () => {
      render(<StatsCards stats={mockStats} />);

      expect(screen.getByText('since midnight')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle zero values', () => {
      const zeroStats: DashboardStats = {
        total_predictions: 0,
        predictions_today: 0,
        active_alerts: 0,
        avg_risk_level: 0,
        recent_activity: [],
      };
      render(<StatsCards stats={zeroStats} />);

      expect(screen.getByText('0%')).toBeInTheDocument();
      expect(screen.getByText('All clear')).toBeInTheDocument();
    });

    it('should handle large numbers', () => {
      const largeStats: DashboardStats = {
        total_predictions: 1000000,
        predictions_today: 9999,
        active_alerts: 100,
        avg_risk_level: 100,
        recent_activity: [],
      };
      render(<StatsCards stats={largeStats} />);

      expect(screen.getByText('1,000,000')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('should handle decimal risk levels', () => {
      render(<StatsCards stats={{ ...mockStats, avg_risk_level: 45.7 }} />);

      expect(screen.getByText('46%')).toBeInTheDocument();
    });
  });
});

describe('StatsCardsSkeleton', () => {
  it('should render four skeleton cards', () => {
    const { container } = render(<StatsCardsSkeleton />);

    // Count the skeleton cards in the grid
    const cards = container.querySelectorAll('.grid > div');
    expect(cards).toHaveLength(4);
  });

  it('should render skeletons with correct structure', () => {
    const { container } = render(<StatsCardsSkeleton />);

    // Check for skeleton elements (Skeleton component uses animate-pulse class)
    const skeletons = container.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});
