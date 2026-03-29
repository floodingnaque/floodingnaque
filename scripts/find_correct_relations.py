"""Find correct OSM barangay relations by searching near known centers."""
import json

with open("scripts/paranaque_boundaries_raw.json") as f:
    data = json.load(f)

# Known centers for the 10 mismatched barangays
MISMATCHED = {
    "san_dionisio": (14.507, 121.007),
    "vitalez": (14.495, 120.991),
    "marcelo_green": (14.482, 121.01),
    "merville": (14.472, 121.036),
    "moonwalk": (14.454, 121.01),
    "san_antonio": (14.468, 121.014),
    "san_isidro": (14.45, 121.03),
    "san_martin": (14.461, 121.0),
    "santo_nino": (14.445, 121.017),
    "sucat": (14.4625, 121.0456),
}


def extract_outer_ring(members):
    outer_ways = []
    for m in members:
        if m.get("role") == "outer" and m.get("type") == "way":
            coords = [(g["lat"], g["lon"]) for g in m.get("geometry", [])]
            if coords:
                outer_ways.append(coords)
    if not outer_ways:
        return []
    ring = list(outer_ways[0])
    remaining = list(outer_ways[1:])
    max_iter = len(remaining) * 2
    while remaining and max_iter > 0:
        max_iter -= 1
        merged = False
        for i, way in enumerate(remaining):
            if not way:
                continue
            if abs(ring[-1][0] - way[0][0]) < 1e-7 and abs(ring[-1][1] - way[0][1]) < 1e-7:
                ring.extend(way[1:])
                remaining.pop(i)
                merged = True
                break
            if abs(ring[-1][0] - way[-1][0]) < 1e-7 and abs(ring[-1][1] - way[-1][1]) < 1e-7:
                ring.extend(reversed(way[:-1]))
                remaining.pop(i)
                merged = True
                break
        if not merged:
            break
    return ring


def centroid(coords):
    if not coords:
        return (0, 0)
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return sum(lats)/len(lats), sum(lons)/len(lons)


def point_in_polygon(point, polygon):
    """Ray casting to check if point is inside polygon."""
    x, y = point
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


# For each mismatched barangay, find which relation contains its known center
for key, (lat, lon) in MISMATCHED.items():
    print(f"\n--- {key} (looking near {lat}, {lon}) ---")
    candidates = []
    for el in data["elements"]:
        ring = extract_outer_ring(el.get("members", []))
        if not ring:
            continue
        if point_in_polygon((lat, lon), ring):
            c = centroid(ring)
            name = el.get("tags", {}).get("name", "?")
            candidates.append((el["id"], name, c))
            print(f"  CONTAINS: id={el['id']}, name={name}, centroid=({c[0]:.4f}, {c[1]:.4f})")

    if not candidates:
        # Find closest centroid
        best_dist = 999
        best = None
        for el in data["elements"]:
            ring = extract_outer_ring(el.get("members", []))
            if not ring:
                continue
            c = centroid(ring)
            dist = ((c[0]-lat)**2 + (c[1]-lon)**2)**0.5
            if dist < best_dist:
                best_dist = dist
                name = el.get("tags", {}).get("name", "?")
                best = (el["id"], name, c, dist)
        if best:
            print(f"  CLOSEST: id={best[0]}, name={best[1]}, centroid=({best[2][0]:.4f}, {best[2][1]:.4f}), dist={best[3]:.4f}")
