/**
 * Geo Worker
 *
 * Offloads GeoJSON processing: point-in-polygon checks, feature
 * filtering, and bounding-box computations for the flood map.
 */

import booleanPointInPolygon from "@turf/boolean-point-in-polygon";
import { point as turfPoint } from "@turf/helpers";
import { expose } from "comlink";

export interface GeoPoint {
  lat: number;
  lng: number;
}

export interface GeoBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

/**
 * Check if a point falls within a bounding box.
 */
function isInBounds(point: GeoPoint, bounds: GeoBounds): boolean {
  return (
    point.lat >= bounds.south &&
    point.lat <= bounds.north &&
    point.lng >= bounds.west &&
    point.lng <= bounds.east
  );
}

/**
 * Filter an array of GeoJSON-like features to only those whose
 * centroid lies within the given bounds.
 */
function filterFeaturesByBounds(
  features: Array<{
    geometry: { coordinates: number[][] | number[][][] };
    properties: Record<string, unknown>;
  }>,
  bounds: GeoBounds,
): typeof features {
  return features.filter((f) => {
    // Attempt to compute a centroid from the first ring of coordinates
    const coords =
      f.geometry.coordinates.length > 0 &&
      Array.isArray(f.geometry.coordinates[0]?.[0])
        ? (f.geometry.coordinates[0] as number[][])
        : (f.geometry.coordinates as number[][]);

    if (!coords || coords.length === 0) return false;

    let sumLat = 0;
    let sumLng = 0;
    for (const c of coords) {
      sumLng += c[0] ?? 0;
      sumLat += c[1] ?? 0;
    }
    const centroid: GeoPoint = {
      lat: sumLat / coords.length,
      lng: sumLng / coords.length,
    };
    return isInBounds(centroid, bounds);
  });
}

/**
 * Compute the bounding box of a set of point coordinates.
 */
function computeBounds(points: GeoPoint[]): GeoBounds | null {
  if (points.length === 0) return null;
  let north = -Infinity;
  let south = Infinity;
  let east = -Infinity;
  let west = Infinity;
  for (const p of points) {
    if (p.lat > north) north = p.lat;
    if (p.lat < south) south = p.lat;
    if (p.lng > east) east = p.lng;
    if (p.lng < west) west = p.lng;
  }
  return { north, south, east, west };
}

/**
 * Detect which barangay a point falls within using Turf.js
 * point-in-polygon against a GeoJSON FeatureCollection.
 */
function detectBarangay(
  lat: number,
  lng: number,
  boundaries: GeoJSON.FeatureCollection,
): string | null {
  const pt = turfPoint([lng, lat]);
  for (const feature of boundaries.features) {
    if (
      (feature.geometry.type === "Polygon" ||
        feature.geometry.type === "MultiPolygon") &&
      booleanPointInPolygon(
        pt,
        feature as GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon>,
      )
    ) {
      return (feature.properties?.name as string) ?? null;
    }
  }
  return null;
}

const geoWorkerApi = {
  isInBounds,
  filterFeaturesByBounds,
  computeBounds,
  detectBarangay,
};

export type GeoWorkerApi = typeof geoWorkerApi;

expose(geoWorkerApi);
