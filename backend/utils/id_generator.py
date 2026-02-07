"""
Utility for generating unique trip IDs.
"""
import uuid
from datetime import datetime


def generate_trip_id() -> str:
    """
    Generate a unique trip ID.

    Returns:
        Unique trip ID string (e.g., "trip_20240207_a3f2b1c4")
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_suffix = uuid.uuid4().hex[:8]
    return f"trip_{timestamp}_{unique_suffix}"


def generate_itinerary_id(trip_id: str) -> str:
    """
    Generate an itinerary ID based on trip ID.

    Args:
        trip_id: The associated trip ID

    Returns:
        Itinerary ID string
    """
    return f"itinerary_{trip_id}"
