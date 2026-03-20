/**
 * FloodMap Component Tests
 *
 * Basic tests for the FloodMap component rendering and behavior.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FloodMap } from "../FloodMap";

// Mock react-leaflet since it requires a DOM with actual dimensions
vi.mock("react-leaflet", () => ({
  MapContainer: ({
    children,
    ...props
  }: {
    children?: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <div data-testid="map-container" {...props}>
      {children}
    </div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  useMapEvents: () => null,
}));

vi.mock("leaflet/dist/leaflet.css", () => ({}));

describe("FloodMap", () => {
  it("renders the map container", () => {
    render(<FloodMap />);
    expect(screen.getByTestId("map-container")).toBeInTheDocument();
  });

  it("renders with custom className", () => {
    render(<FloodMap className="custom-class" />);
    const container = screen.getByTestId("map-container");
    expect(container).toBeInTheDocument();
  });

  it("renders tile layer", () => {
    render(<FloodMap />);
    expect(screen.getByTestId("tile-layer")).toBeInTheDocument();
  });
});
