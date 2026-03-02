/**
 * RiskDisplay Component Tests
 *
 * Tests for the RiskDisplay component that shows flood risk level
 * with color-coded visual feedback and probability indicator.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/utils';
import { RiskDisplay } from '@/features/flooding/components/RiskDisplay';
import type { RiskLevel } from '@/types';

describe('RiskDisplay', () => {
  describe('Risk Level Rendering', () => {
    it('should display Safe label for risk level 0', () => {
      render(<RiskDisplay riskLevel={0} probability={0.15} />);
      expect(screen.getByText('Safe')).toBeInTheDocument();
    });

    it('should display Alert label for risk level 1', () => {
      render(<RiskDisplay riskLevel={1} probability={0.6} />);
      expect(screen.getByText('Alert')).toBeInTheDocument();
    });

    it('should display Critical label for risk level 2', () => {
      render(<RiskDisplay riskLevel={2} probability={0.92} />);
      expect(screen.getByText('Critical')).toBeInTheDocument();
    });

    it('should display correct risk level number', () => {
      render(<RiskDisplay riskLevel={1} probability={0.65} />);
      expect(screen.getByText('Risk Level 1')).toBeInTheDocument();
    });
  });

  describe('Probability Display', () => {
    it('should display probability as a percentage', () => {
      render(<RiskDisplay riskLevel={1} probability={0.75} />);
      // Percentage appears in both the main display and the progress bar label
      expect(screen.getAllByText('75%').length).toBeGreaterThanOrEqual(1);
    });

    it('should display 0% for probability 0', () => {
      render(<RiskDisplay riskLevel={0} probability={0} />);
      expect(screen.getAllByText('0%').length).toBeGreaterThanOrEqual(1);
    });

    it('should display 100% for probability 1', () => {
      render(<RiskDisplay riskLevel={2} probability={1} />);
      expect(screen.getAllByText('100%').length).toBeGreaterThanOrEqual(1);
    });

    it('should round probability to nearest integer', () => {
      render(<RiskDisplay riskLevel={1} probability={0.667} />);
      expect(screen.getAllByText('67%').length).toBeGreaterThanOrEqual(1);
    });

    it('should display "Flood Probability" label', () => {
      render(<RiskDisplay riskLevel={0} probability={0.2} />);
      expect(screen.getByText('Flood Probability')).toBeInTheDocument();
    });
  });

  describe('Confidence Levels', () => {
    it('should show Very High Confidence for probability >= 0.9', () => {
      render(<RiskDisplay riskLevel={2} probability={0.95} />);
      expect(screen.getByText('Very High Confidence')).toBeInTheDocument();
    });

    it('should show High Confidence for probability >= 0.75', () => {
      render(<RiskDisplay riskLevel={1} probability={0.8} />);
      expect(screen.getByText('High Confidence')).toBeInTheDocument();
    });

    it('should show Moderate Confidence for probability >= 0.5', () => {
      render(<RiskDisplay riskLevel={1} probability={0.55} />);
      expect(screen.getByText('Moderate Confidence')).toBeInTheDocument();
    });

    it('should show Low Confidence for probability >= 0.25', () => {
      render(<RiskDisplay riskLevel={0} probability={0.3} />);
      expect(screen.getByText('Low Confidence')).toBeInTheDocument();
    });

    it('should show Very Low Confidence for probability < 0.25', () => {
      render(<RiskDisplay riskLevel={0} probability={0.1} />);
      expect(screen.getByText('Very Low Confidence')).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply green color classes for risk level 0', () => {
      const { container } = render(<RiskDisplay riskLevel={0} probability={0.15} />);
      const heading = screen.getByText('Safe');
      expect(heading.className).toContain('text-green-600');
      // Background should be green
      expect(container.firstChild).toHaveClass('bg-green-100');
    });

    it('should apply amber color classes for risk level 1', () => {
      const { container } = render(<RiskDisplay riskLevel={1} probability={0.65} />);
      const heading = screen.getByText('Alert');
      expect(heading.className).toContain('text-amber-600');
      expect(container.firstChild).toHaveClass('bg-amber-100');
    });

    it('should apply red color classes for risk level 2', () => {
      const { container } = render(<RiskDisplay riskLevel={2} probability={0.9} />);
      const heading = screen.getByText('Critical');
      expect(heading.className).toContain('text-red-600');
      expect(container.firstChild).toHaveClass('bg-red-100');
    });

    it('should apply custom className when provided', () => {
      const { container } = render(
        <RiskDisplay riskLevel={0} probability={0.2} className="my-custom-class" />,
      );
      expect(container.firstChild).toHaveClass('my-custom-class');
    });
  });

  describe('All Risk Levels', () => {
    const cases: Array<{ level: RiskLevel; label: string; prob: number }> = [
      { level: 0, label: 'Safe', prob: 0.1 },
      { level: 1, label: 'Alert', prob: 0.6 },
      { level: 2, label: 'Critical', prob: 0.95 },
    ];

    cases.forEach(({ level, label, prob }) => {
      it(`should render correctly for risk level ${level} (${label})`, () => {
        render(<RiskDisplay riskLevel={level} probability={prob} />);
        expect(screen.getByText(label)).toBeInTheDocument();
        // Percentage appears in both the main display and the progress bar label
        expect(screen.getAllByText(`${Math.round(prob * 100)}%`).length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText(`Risk Level ${level}`)).toBeInTheDocument();
      });
    });
  });
});
