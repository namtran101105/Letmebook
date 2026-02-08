"""ID generation utilities."""
import uuid
from datetime import datetime


def generate_trip_id() -> str:
    """
    Generate a unique trip ID.
    
    Format: trip_{timestamp}_{uuid_short}
    Example: trip_20260208_a3f2d1c4
    
    Returns:
        str: A unique trip identifier
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    uuid_short = str(uuid.uuid4())[:8]
    return f"trip_{timestamp}_{uuid_short}"


def generate_session_id() -> str:
    """
    Generate a unique session ID.
    
    Returns:
        str: A unique session identifier
    """
    return str(uuid.uuid4())
