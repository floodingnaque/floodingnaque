"""Chat feature constants - single source of truth for channel validation."""

VALID_BARANGAY_IDS = frozenset({
    "baclaran", "bf_homes", "don_bosco", "don_galo", "la_huerta",
    "marcelo_green", "merville", "moonwalk", "san_antonio",
    "san_dionisio", "san_isidro", "san_martin_de_porres",
    "sto_nino", "sun_valley", "tambo", "vitalez", "citywide",
})

BARANGAY_DISPLAY_NAMES = {
    "baclaran": "Baclaran",
    "bf_homes": "BF Homes",
    "don_bosco": "Don Bosco",
    "don_galo": "Don Galo",
    "la_huerta": "La Huerta",
    "marcelo_green": "Marcelo Green",
    "merville": "Merville",
    "moonwalk": "Moonwalk",
    "san_antonio": "San Antonio",
    "san_dionisio": "San Dionisio",
    "san_isidro": "San Isidro",
    "san_martin_de_porres": "San Martin de Porres",
    "sto_nino": "Santo Niño",
    "sun_valley": "Sun Valley",
    "tambo": "Tambo",
    "vitalez": "Vitalez",
    "citywide": "City-Wide Broadcast",
}

# Only these roles can post to the citywide channel
CITYWIDE_POSTER_ROLES = frozenset({"operator", "admin"})

VALID_MESSAGE_TYPES = frozenset({
    "text", "alert", "status_update", "flood_report",
})

DEFAULT_MESSAGE_LIMIT = 50
MAX_MESSAGE_LIMIT = 100
MAX_MESSAGE_LENGTH = 1000
