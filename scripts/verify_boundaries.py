"""Verify extracted polygons against known barangay centers."""
import json
import math

# Known centers from paranaque.ts
KNOWN_CENTERS = {
    "baclaran": (14.524, 121.001),
    "don_galo": (14.512, 120.992),
    "la_huerta": (14.4891, 120.9876),
    "san_dionisio": (14.507, 121.007),
    "tambo": (14.518, 120.995),
    "vitalez": (14.495, 120.991),
    "bf_homes": (14.4545, 121.0234),
    "don_bosco": (14.476, 121.024),
    "marcelo_green": (14.482, 121.01),
    "merville": (14.472, 121.036),
    "moonwalk": (14.454, 121.01),
    "san_antonio": (14.468, 121.014),
    "san_isidro": (14.45, 121.03),
    "san_martin": (14.461, 121.0),
    "santo_nino": (14.445, 121.017),
    "sucat": (14.4625, 121.0456),
}

with open("scripts/paranaque_polygons_simplified.json") as f:
    polygons = json.load(f)

def centroid(coords):
    lats = [c[0] for c in coords[:-1]]  # skip closing point
    lons = [c[1] for c in coords[:-1]]
    return sum(lats)/len(lats), sum(lons)/len(lons)

def distance_km(p1, p2):
    dlat = (p1[0]-p2[0]) * 111.32
    dlon = (p1[1]-p2[1]) * 111.32 * math.cos(math.radians(14.48))
    return math.sqrt(dlat**2 + dlon**2)

print(f"{'Barangay':<20} {'Known Center':>25} {'Polygon Centroid':>25} {'Dist (km)':>10} {'OK?':>5}")
print("-" * 90)

for key, known in KNOWN_CENTERS.items():
    if key in polygons:
        c = centroid(polygons[key])
        dist = distance_km(known, c)
        ok = "YES" if dist < 1.5 else "NO"
        print(f"{key:<20} ({known[0]:.4f}, {known[1]:.4f})   ({c[0]:.4f}, {c[1]:.4f})   {dist:>8.2f}   {ok:>5}")
    else:
        print(f"{key:<20} NOT FOUND")
