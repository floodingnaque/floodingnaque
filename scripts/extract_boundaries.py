"""Extract and simplify Parañaque barangay polygons from OSM data."""
import json
import math

# Parañaque barangay OSM relation IDs
PARANAQUE_BARANGAYS = {
    "baclaran": 156053,
    "don_galo": 153195,
    "la_huerta": 153198,
    "san_dionisio": 1561593,
    "tambo": 153196,
    "vitalez": 156062,
    "bf_homes": 6282328,
    "don_bosco": 1016376,
    "marcelo_green": 3676842,
    "merville": 156100,
    "moonwalk": 153199,
    "san_antonio": 6116611,
    "san_isidro": 1772565,
    "san_martin": 1561592,
    "santo_nino": 153197,
    "sucat": 156096,
}

def extract_outer_ring(members):
    """Extract outer ring coordinates from relation members."""
    outer_ways = []
    for m in members:
        if m.get("role") == "outer" and m.get("type") == "way":
            coords = [(g["lat"], g["lon"]) for g in m.get("geometry", [])]
            if coords:
                outer_ways.append(coords)

    if not outer_ways:
        return []

    # Merge consecutive ways into a single ring
    ring = list(outer_ways[0])
    remaining = list(outer_ways[1:])
    max_iter = len(remaining) * 2

    while remaining and max_iter > 0:
        max_iter -= 1
        merged = False
        for i, way in enumerate(remaining):
            if not way:
                continue
            # Check if this way connects to the end of the ring
            if abs(ring[-1][0] - way[0][0]) < 1e-7 and abs(ring[-1][1] - way[0][1]) < 1e-7:
                ring.extend(way[1:])
                remaining.pop(i)
                merged = True
                break
            # Check reversed
            if abs(ring[-1][0] - way[-1][0]) < 1e-7 and abs(ring[-1][1] - way[-1][1]) < 1e-7:
                ring.extend(reversed(way[:-1]))
                remaining.pop(i)
                merged = True
                break
        if not merged:
            break

    return ring


def simplify_polygon(coords, max_points=20):
    """Simplify polygon using Ramer-Douglas-Peucker algorithm."""
    if len(coords) <= max_points:
        return coords

    def perpendicular_distance(point, start, end):
        if start == end:
            return math.sqrt((point[0] - start[0])**2 + (point[1] - start[1])**2)
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        d = dx * dx + dy * dy
        t = max(0, min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / d))
        proj = (start[0] + t * dx, start[1] + t * dy)
        return math.sqrt((point[0] - proj[0])**2 + (point[1] - proj[1])**2)

    def rdp(points, epsilon):
        if len(points) <= 2:
            return points
        dmax = 0
        idx = 0
        for i in range(1, len(points) - 1):
            d = perpendicular_distance(points[i], points[0], points[-1])
            if d > dmax:
                dmax = d
                idx = i
        if dmax > epsilon:
            left = rdp(points[:idx + 1], epsilon)
            right = rdp(points[idx:], epsilon)
            return left[:-1] + right
        else:
            return [points[0], points[-1]]

    # Binary search for epsilon that gives ~max_points
    lo, hi = 0.0, 0.01
    result = coords
    for _ in range(30):
        mid = (lo + hi) / 2
        simplified = rdp(coords, mid)
        if len(simplified) > max_points:
            lo = mid
        else:
            hi = mid
            result = simplified

    return result


def main():
    with open("scripts/paranaque_boundaries_raw.json") as f:
        data = json.load(f)

    elements_by_id = {el["id"]: el for el in data["elements"]}
    output = {}

    for key, rel_id in PARANAQUE_BARANGAYS.items():
        el = elements_by_id.get(rel_id)
        if not el:
            print(f"  WARNING: {key} (id={rel_id}) not found in data!")
            continue

        members = el.get("members", [])
        ring = extract_outer_ring(members)

        if not ring:
            print(f"  WARNING: {key} has no outer ring geometry!")
            continue

        # Simplify to max 20 points for frontend performance
        simplified = simplify_polygon(ring, max_points=20)

        # Ensure polygon is closed
        if simplified[0] != simplified[-1]:
            simplified.append(simplified[0])

        # Round to 6 decimal places
        simplified = [[round(lat, 6), round(lon, 6)] for lat, lon in simplified]

        output[key] = simplified
        print(f"  {key}: {len(ring)} points -> {len(simplified)} simplified")

    # Output as TypeScript-friendly format
    print("\n// ---- Copy below into paranaque.ts ----")
    for key, coords in output.items():
        coord_str = ",\n      ".join(f"[{c[0]}, {c[1]}]" for c in coords)
        print(f'    // {key}')
        print(f'    polygon: [\n      {coord_str}\n    ],')
        print()

    # Also save as JSON for reference
    with open("scripts/paranaque_polygons_simplified.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Saved simplified polygons to scripts/paranaque_polygons_simplified.json")


if __name__ == "__main__":
    main()
