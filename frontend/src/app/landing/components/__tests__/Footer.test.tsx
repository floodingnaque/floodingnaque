/**
 * Footer Component Tests
 *
 * Tests for the landing page Footer component.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/utils';
import { Footer } from '@/app/landing/components/Footer';

describe('Footer', () => {
  it('should render the brand name', () => {
    render(<Footer />);
    expect(screen.getByText('Floodingnaque')).toBeInTheDocument();
  });

  it('should render the developer credit', () => {
    render(<Footer />);
    expect(screen.getByText(/Developed by Ramil & Friends/)).toBeInTheDocument();
  });

  it('should render the current year in copyright', () => {
    render(<Footer />);
    const year = new Date().getFullYear().toString();
    expect(screen.getByText(new RegExp(year))).toBeInTheDocument();
  });

  it('should render system links pointing to login routes', () => {
    render(<Footer />);
    expect(screen.getByText('Resident Dashboard')).toBeInTheDocument();
    expect(screen.getByText('LGU Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Admin Portal')).toBeInTheDocument();
  });

  it('should render correct GitHub link', () => {
    render(<Footer />);
    const sourceLink = screen.getByText('Source Code');
    expect(sourceLink.closest('a')).toHaveAttribute(
      'href',
      'https://github.com/KyaRhamil/floodingnaque',
    );
  });

  it('should mention Flask (not FastAPI) in tech stack', () => {
    render(<Footer />);
    expect(screen.getByText(/Flask/)).toBeInTheDocument();
    expect(screen.queryByText(/FastAPI/)).not.toBeInTheDocument();
  });

  it('should not mention Asian Institute of Computer Studies', () => {
    render(<Footer />);
    expect(screen.queryByText(/Asian Institute of Computer Studies/)).not.toBeInTheDocument();
  });
});
