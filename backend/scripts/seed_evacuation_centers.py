"""Seed Evacuation Centers — populate evacuation_centers table.

Inserts 16 evacuation centers (one per Parañaque barangay) with
capacity estimates based on typical Philippine facility sizes.

Usage:
    python scripts/seed_evacuation_centers.py

Idempotent: skips centres that already exist (matched on name + barangay).
"""

import os
import sys
from pathlib import Path

# Ensure the backend package is importable
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Load .env BEFORE importing app modules (security.py validates JWT_SECRET_KEY at import)
from dotenv import load_dotenv

env_name = os.getenv("APP_ENV", "development")
env_file = backend_dir / f".env.{env_name}"
if env_file.exists():
    load_dotenv(env_file, override=True)

from app.models.db import get_db_session
from app.models.evacuation_center import EvacuationCenter

# ── Evacuation center data ───────────────────────────────────────────────
# Coordinates sourced from BARANGAY_META in gis_service.py.
# Capacities are estimates: schools → 300–500, covered courts → 150–250,
# barangay halls → 100–200.

CENTERS = [
    {
        "name": "Baclaran Elementary School",
        "barangay": "Baclaran",
        "address": "M.H. Del Pilar St, Baclaran, Parañaque City",
        "latitude": 14.5245,
        "longitude": 121.0005,
        "capacity_total": 350,
        "contact_number": "(02) 8826-1234",
    },
    {
        "name": "Don Galo Covered Court",
        "barangay": "Don Galo",
        "address": "Don Galo St, Parañaque City",
        "latitude": 14.5125,
        "longitude": 120.9915,
        "capacity_total": 200,
        "contact_number": "(02) 8826-2345",
    },
    {
        "name": "La Huerta National High School",
        "barangay": "La Huerta",
        "address": "La Huerta, Parañaque City",
        "latitude": 14.4895,
        "longitude": 120.9870,
        "capacity_total": 450,
        "contact_number": "(02) 8826-3456",
    },
    {
        "name": "San Dionisio Barangay Hall",
        "barangay": "San Dionisio",
        "address": "San Dionisio, Parañaque City",
        "latitude": 14.5075,
        "longitude": 121.0065,
        "capacity_total": 150,
        "contact_number": "(02) 8826-4567",
    },
    {
        "name": "Tambo Elementary School",
        "barangay": "Tambo",
        "address": "Tambo, Parañaque City",
        "latitude": 14.5185,
        "longitude": 120.9945,
        "capacity_total": 400,
        "contact_number": "(02) 8826-5678",
    },
    {
        "name": "Vitalez Covered Court",
        "barangay": "Vitalez",
        "address": "Vitalez, Parañaque City",
        "latitude": 14.4955,
        "longitude": 120.9905,
        "capacity_total": 180,
        "contact_number": "(02) 8826-6789",
    },
    {
        "name": "BF Homes Parañaque National High School",
        "barangay": "BF Homes",
        "address": "Aguirre Ave, BF Homes, Parañaque City",
        "latitude": 14.4550,
        "longitude": 121.0230,
        "capacity_total": 500,
        "contact_number": "(02) 8826-7890",
    },
    {
        "name": "Don Bosco Barangay Hall",
        "barangay": "Don Bosco",
        "address": "Don Bosco, Parañaque City",
        "latitude": 14.4765,
        "longitude": 121.0235,
        "capacity_total": 200,
        "contact_number": "(02) 8826-8901",
    },
    {
        "name": "Marcelo Green Covered Court",
        "barangay": "Marcelo Green Village",
        "address": "Marcelo Green Village, Parañaque City",
        "latitude": 14.4825,
        "longitude": 121.0095,
        "capacity_total": 250,
        "contact_number": "(02) 8826-9012",
    },
    {
        "name": "Merville Elementary School",
        "barangay": "Merville",
        "address": "Merville Park Subdivision, Parañaque City",
        "latitude": 14.4725,
        "longitude": 121.0355,
        "capacity_total": 350,
        "contact_number": "(02) 8826-0123",
    },
    {
        "name": "Moonwalk Covered Court",
        "barangay": "Moonwalk",
        "address": "Moonwalk, Parañaque City",
        "latitude": 14.4545,
        "longitude": 121.0095,
        "capacity_total": 300,
        "contact_number": "(02) 8827-1234",
    },
    {
        "name": "San Antonio Barangay Hall",
        "barangay": "San Antonio",
        "address": "San Antonio Valley, Parañaque City",
        "latitude": 14.4685,
        "longitude": 121.0135,
        "capacity_total": 180,
        "contact_number": "(02) 8827-2345",
    },
    {
        "name": "San Isidro Elementary School",
        "barangay": "San Isidro",
        "address": "San Isidro, Parañaque City",
        "latitude": 14.4505,
        "longitude": 121.0295,
        "capacity_total": 400,
        "contact_number": "(02) 8827-3456",
    },
    {
        "name": "San Martin de Porres Covered Court",
        "barangay": "San Martin de Porres",
        "address": "San Martin de Porres, Parañaque City",
        "latitude": 14.4615,
        "longitude": 120.9995,
        "capacity_total": 250,
        "contact_number": "(02) 8827-4567",
    },
    {
        "name": "Santo Niño Elementary School",
        "barangay": "Santo Niño",
        "address": "Santo Niño, Parañaque City",
        "latitude": 14.4455,
        "longitude": 121.0165,
        "capacity_total": 350,
        "contact_number": "(02) 8827-5678",
    },
    {
        "name": "Sucat (Sun Valley) Barangay Hall",
        "barangay": "Sun Valley (Sucat)",
        "address": "Dr. A. Santos Ave, Sucat, Parañaque City",
        "latitude": 14.4630,
        "longitude": 121.0450,
        "capacity_total": 200,
        "contact_number": "(02) 8827-6789",
    },
]


def seed_centers() -> int:
    """Insert evacuation centers (idempotent). Returns count of newly inserted."""
    inserted = 0

    with get_db_session() as session:
        for data in CENTERS:
            exists = (
                session.query(EvacuationCenter)
                .filter(
                    EvacuationCenter.name == data["name"],
                    EvacuationCenter.barangay == data["barangay"],
                )
                .first()
            )
            if exists:
                print(f"  [skip] {data['name']} ({data['barangay']}) already exists")
                continue

            center = EvacuationCenter(**data)
            session.add(center)
            inserted += 1
            print(f"  [add]  {data['name']} ({data['barangay']})")

    return inserted


if __name__ == "__main__":
    print("Seeding evacuation centers...")
    count = seed_centers()
    print(f"\nDone — {count} new center(s) inserted, {len(CENTERS) - count} skipped.")
