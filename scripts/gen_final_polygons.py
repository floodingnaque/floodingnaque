"""Generate updated paranaque.ts polygon data from verified OSM boundaries."""
import json
import math

# OSM relation IDs - all confirmed Paranaque barangays
PARANAQUE_IDS = {
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
    max_iter = len(remaining) * 3
    while remaining and max_iter > 0:
        max_iter -= 1
        merged = False
        for i, way in enumerate(remaining):
            if not way:
                continue
            if abs(ring[-1][0] - way[0][0]) < 1e-6 and abs(ring[-1][1] - way[0][1]) < 1e-6:
                ring.extend(way[1:])
                remaining.pop(i)
                merged = True
                break
            if abs(ring[-1][0] - way[-1][0]) < 1e-6 and abs(ring[-1][1] - way[-1][1]) < 1e-6:
                ring.extend(list(reversed(way))[1:])
                remaining.pop(i)
                merged = True
                break
        if not merged:
            break
    return ring


def simplify_rdp(points, max_points=24):
    if len(points) <= max_points:
        return points

    def perp_dist(p, a, b):
        if a == b:
            return math.sqrt((p[0]-a[0])**2 + (p[1]-a[1])**2)
        dx, dy = b[0]-a[0], b[1]-a[1]
        d2 = dx*dx + dy*dy
        t = max(0, min(1, ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / d2))
        px, py = a[0]+t*dx, a[1]+t*dy
        return math.sqrt((p[0]-px)**2 + (p[1]-py)**2)

    def rdp(pts, eps):
        if len(pts) <= 2:
            return pts
        dmax, idx = 0, 0
        for i in range(1, len(pts)-1):
            d = perp_dist(pts[i], pts[0], pts[-1])
            if d > dmax:
                dmax, idx = d, i
        if dmax > eps:
            return rdp(pts[:idx+1], eps)[:-1] + rdp(pts[idx:], eps)
        return [pts[0], pts[-1]]

    lo, hi = 0.0, 0.01
    result = points
    for _ in range(40):
        mid = (lo + hi) / 2
        s = rdp(points, mid)
        if len(s) > max_points:
            lo = mid
        else:
            hi = mid
            result = s
    return result


def centroid(coords):
    pts = coords if coords[0] != coords[-1] else coords[:-1]
    lats = [c[0] for c in pts]
    lons = [c[1] for c in pts]
    return round(sum(lats)/len(lats), 4), round(sum(lons)/len(lons), 4)


with open("scripts/paranaque_boundaries_raw.json") as f:
    data = json.load(f)

elements_by_id = {el["id"]: el for el in data["elements"]}

results = {}
for key, rel_id in PARANAQUE_IDS.items():
    el = elements_by_id[rel_id]
    ring = extract_outer_ring(el.get("members", []))
    simplified = simplify_rdp(ring, max_points=24)
    if simplified[0] != simplified[-1]:
        simplified.append(simplified[0])
    simplified = [[round(lat, 6), round(lon, 6)] for lat, lon in simplified]
    c = centroid(simplified)
    results[key] = {"polygon": simplified, "centroid": c}
    name = el.get("tags", {}).get("name", key)
    print(f"{key}: {name} -> centroid ({c[0]}, {c[1]}), {len(simplified)} pts")

# Save for use
with open("scripts/paranaque_final_polygons.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved to scripts/paranaque_final_polygons.json")
