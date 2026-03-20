import logging


def setup_logging():
    """Setup logging configuration using the shared logging helper."""
    from app.utils.observability import logging as logging_utils

    return logging_utils.setup_logging()


def error_handler(func):
    """Decorator for error handling."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {str(e)}")
            raise

    return wrapper


def validate_coordinates(lat, lon):
    """Validate latitude and longitude coordinates."""
    if lat is not None:
        if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
            raise ValueError("Latitude must be between -90 and 90")
    if lon is not None:
        if not isinstance(lon, (int, float)) or lon < -180 or lon > 180:
            raise ValueError("Longitude must be between -180 and 180")
    return True
