"""Fetch Parañaque barangay boundaries from OpenStreetMap Overpass API."""
import json
import urllib.request

query = """[out:json][timeout:120];
(
  rel[admin_level=10][boundary=administrative](14.43,120.97,14.54,121.06);
);
out geom;"""

url = "https://overpass-api.de/api/interpreter"
data = ("data=" + query).encode("utf-8")
req = urllib.request.Request(url, data=data, method="POST")
req.add_header("Content-Type", "application/x-www-form-urlencoded")

print("Fetching boundaries...")
resp = urllib.request.urlopen(req, timeout=120)
result = json.loads(resp.read().decode("utf-8"))
elements = result.get("elements", [])
print(f"Found {len(elements)} relations")

for el in elements:
    tags = el.get("tags", {})
    name = tags.get("name", "Unknown")
    rid = el["id"]
    print(f"  - {name} (id={rid})")

# Save raw data
with open("scripts/paranaque_boundaries_raw.json", "w") as f:
    json.dump(result, f, indent=2)
print("Saved to scripts/paranaque_boundaries_raw.json")
