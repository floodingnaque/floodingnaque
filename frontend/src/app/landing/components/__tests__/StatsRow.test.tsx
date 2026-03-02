/**
 * StatsRow Component Tests
 *
 * Tests for the landing page StatsRow component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/utils';
import { StatsRow } from '@/app/landing/components/StatsRow';

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual<typeof import('framer-motion')>('framer-motion');
  return {
    ...actual,
    motion: {
      ...actual.motion,
      div: 'div',
    },
    useInView: () => true,
  };
});

describe('StatsRow', () => {
  it('should render all four stat labels', () => {
    render(<StatsRow />);
    expect(screen.getByText('Official Flood Records')).toBeInTheDocument();
    expect(screen.getByText('Model Accuracy')).toBeInTheDocument();
    expect(screen.getByText('Barangays Monitored')).toBeInTheDocument();
    expect(screen.getByText('Training Samples')).toBeInTheDocument();
  });

  it('should render source descriptions', () => {
    render(<StatsRow />);
    expect(screen.getByText(/DRRMO 2022–2025/)).toBeInTheDocument();
    expect(screen.getByText('Random Forest v6')).toBeInTheDocument();
    expect(screen.getByText(/All barangays/)).toBeInTheDocument();
    expect(screen.getByText(/Balanced flood/)).toBeInTheDocument();
  });

  it('should have a stats section with correct id', () => {
    const { container } = render(<StatsRow />);
    const section = container.querySelector('#stats');
    expect(section).toBeInTheDocument();
  });
});
