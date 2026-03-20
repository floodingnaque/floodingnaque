/**
 * Navbar Component Tests
 *
 * Tests for the landing page Navbar component.
 */

import { Navbar } from "@/app/landing/components/Navbar";
import { render, screen } from "@/test/utils";
import { beforeAll, describe, expect, it, vi } from "vitest";

// IntersectionObserver is not available in jsdom
beforeAll(() => {
  class MockIntersectionObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
    constructor() {}
  }
  vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
});

// Mock framer-motion to avoid animation issues in tests
vi.mock("framer-motion", async () => {
  const actual =
    await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return {
    ...actual,
    motion: {
      ...actual.motion,
      div: "div",
      nav: "nav",
    },
  };
});

describe("Navbar", () => {
  it("should render the brand name", () => {
    render(<Navbar />);
    expect(screen.getByText("Floodingnaque")).toBeInTheDocument();
  });

  it("should render navigation links", () => {
    render(<Navbar />);
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("How It Works")).toBeInTheDocument();
    expect(screen.getByText("Features")).toBeInTheDocument();
    expect(screen.getByText("Barangays")).toBeInTheDocument();
    expect(screen.getByText("About")).toBeInTheDocument();
  });

  it("should render Get Started CTA pointing to /login", () => {
    render(<Navbar />);
    const ctaLinks = screen.getAllByText(/Get Started/);
    const desktopLink = ctaLinks[0]!;
    expect(desktopLink.closest("a")).toHaveAttribute("href", "/login");
  });

  it("should have a mobile menu toggle button", () => {
    render(<Navbar />);
    const toggle = screen.getByLabelText("Toggle menu");
    expect(toggle).toBeInTheDocument();
  });
});
