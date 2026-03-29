"""Generate the updated polygon section for paranaque.ts from OSM data."""
import json

with open("scripts/paranaque_final_polygons.json") as f:
    data = json.load(f)

# Original metadata that should be preserved (population, evacuation, risk, etc.)
META = {
    "baclaran": {
        "name": "Baclaran", "population": 36073,
        "evacuationCenter": "Baclaran Elementary School",
        "evacLat": 14.5255, "evacLon": 121.0025,
        "floodRisk": "high", "zone": "Coastal", "area": 2.81, "floodEvents": 7,
    },
    "don_galo": {
        "name": "Don Galo", "population": 16204,
        "evacuationCenter": "Don Galo Elementary School",
        "evacLat": 14.5135, "evacLon": 120.9935,
        "floodRisk": "high", "zone": "Coastal", "area": 1.44, "floodEvents": 0,
    },
    "la_huerta": {
        "name": "La Huerta", "population": 50905,
        "evacuationCenter": "La Huerta Elementary School",
        "evacLat": 14.4905, "evacLon": 120.9895,
        "floodRisk": "high", "zone": "Inland", "area": 2.06, "floodEvents": 2,
    },
    "san_dionisio": {
        "name": "San Dionisio", "population": 32459,
        "evacuationCenter": "San Dionisio Elementary School",
        "evacLat": 14.5085, "evacLon": 121.0055,
        "floodRisk": "moderate", "zone": "Low-lying", "area": 3.22, "floodEvents": 24,
    },
    "tambo": {
        "name": "Tambo", "population": 30709,
        "evacuationCenter": "Tambo Elementary School",
        "evacLat": 14.5195, "evacLon": 120.9965,
        "floodRisk": "high", "zone": "Coastal", "area": 1.93, "floodEvents": 2,
    },
    "vitalez": {
        "name": "Vitalez", "population": 19213,
        "evacuationCenter": "Vitalez Elementary School",
        "evacLat": 14.4965, "evacLon": 120.9925,
        "floodRisk": "moderate", "zone": "Low-lying", "area": 1.48, "floodEvents": 5,
    },
    "bf_homes": {
        "name": "BF Homes", "population": 93023,
        "evacuationCenter": "BF Homes Covered Court / BF Homes Elementary School",
        "evacLat": 14.456, "evacLon": 121.025,
        "floodRisk": "high", "zone": "Inland", "area": 6.34, "floodEvents": 2,
    },
    "don_bosco": {
        "name": "Don Bosco", "population": 72218,
        "evacuationCenter": "Don Bosco Church / Barangay Hall",
        "evacLat": 14.4775, "evacLon": 121.0225,
        "floodRisk": "moderate", "zone": "Inland", "area": 1.92, "floodEvents": 10,
    },
    "marcelo_green": {
        "name": "Marcelo Green Village", "population": 28497,
        "evacuationCenter": "Marcelo Green Elementary School",
        "evacLat": 14.4835, "evacLon": 121.0115,
        "floodRisk": "moderate", "zone": "Low-lying", "area": 2.38, "floodEvents": 11,
    },
    "merville": {
        "name": "Merville", "population": 33580,
        "evacuationCenter": "Merville Covered Court",
        "evacLat": 14.4735, "evacLon": 121.0345,
        "floodRisk": "low", "zone": "Inland", "area": 1.85, "floodEvents": 11,
    },
    "moonwalk": {
        "name": "Moonwalk", "population": 53413,
        "evacuationCenter": "Moonwalk Elementary School",
        "evacLat": 14.4555, "evacLon": 121.0085,
        "floodRisk": "high", "zone": "Low-lying", "area": 1.67, "floodEvents": 11,
    },
    "san_antonio": {
        "name": "San Antonio", "population": 38891,
        "evacuationCenter": "San Antonio Parish Covered Court",
        "evacLat": 14.4695, "evacLon": 121.0125,
        "floodRisk": "moderate", "zone": "Low-lying", "area": 2.97, "floodEvents": 25,
    },
    "san_isidro": {
        "name": "San Isidro", "population": 36542,
        "evacuationCenter": "San Isidro Elementary School",
        "evacLat": 14.4515, "evacLon": 121.0285,
        "floodRisk": "moderate", "zone": "Low-lying", "area": 2.84, "floodEvents": 20,
    },
    "san_martin": {
        "name": "San Martin de Porres", "population": 40104,
        "evacuationCenter": "San Martin Elementary School",
        "evacLat": 14.4625, "evacLon": 121.0015,
        "floodRisk": "moderate", "zone": "Inland", "area": 1.78, "floodEvents": 3,
    },
    "santo_nino": {
        "name": "Santo Niño", "population": 33821,
        "evacuationCenter": "Santo Niño Elementary School",
        "evacLat": 14.4465, "evacLon": 121.0155,
        "floodRisk": "low", "zone": "Low-lying", "area": 1.56, "floodEvents": 11,
    },
    "sucat": {
        "name": "Sun Valley (Sucat)", "population": 50172,
        "evacuationCenter": "Sun Valley Gym / Sucat Elementary School",
        "evacLat": 14.464, "evacLon": 121.047,
        "floodRisk": "moderate", "zone": "Low-lying", "area": 2.15, "floodEvents": 4,
    },
}

ORDER = [
    "baclaran", "don_galo", "la_huerta", "san_dionisio", "tambo", "vitalez",
    "bf_homes", "don_bosco", "marcelo_green", "merville", "moonwalk",
    "san_antonio", "san_isidro", "san_martin", "santo_nino", "sucat",
]

lines = []
for key in ORDER:
    poly = data[key]
    m = META[key]
    clat, clon = poly["centroid"]
    coords = poly["polygon"]

    coord_lines = []
    for c in coords:
        coord_lines.append(f"      [{c[0]}, {c[1]}]")

    lines.append(f"  {{")
    lines.append(f'    key: "{key}",')
    lines.append(f'    name: "{m["name"]}",')
    lines.append(f"    lat: {clat},")
    lines.append(f"    lon: {clon},")
    lines.append(f"    population: {m['population']:_},".replace("_", "_"))
    lines.append(f"    polygon: [")
    lines.append(",\n".join(coord_lines))
    lines.append(f"    ],")
    lines.append(f'    evacuationCenter: "{m["evacuationCenter"]}",')
    lines.append(f"    evacLat: {m['evacLat']},")
    lines.append(f"    evacLon: {m['evacLon']},")
    lines.append(f'    floodRisk: "{m["floodRisk"]}",')
    lines.append(f'    zone: "{m["zone"]}",')
    lines.append(f"    area: {m['area']},")
    lines.append(f"    floodEvents: {m['floodEvents']},")
    lines.append(f"  }},")

print("\n".join(lines))
