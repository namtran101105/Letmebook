"""
Venue service — queries the Airflow-managed PostgreSQL database for place/venue
data that was scraped and stored by the website_change_monitor DAG.

The Flask backend reads from the *same* database that Airflow writes to.
Tables used: places, place_facts (defined in airflow/dags/lib/db.py).

Usage:
    from services.venue_service import VenueService

    svc = VenueService()
    venues = svc.get_venues_for_itinerary(
        city="Toronto",
        interests=["Food and Beverage", "Culture and History"],
        budget_per_day=120.0,
    )
"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Allow imports of airflow lib when running from backend/
_airflow_dags = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "airflow",
    "dags",
)
if _airflow_dags not in sys.path:
    sys.path.insert(0, _airflow_dags)

from config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Interest category → place category mapping
# ---------------------------------------------------------------------------
# The NLP extractor outputs canonical interest names.  The Airflow DB stores
# a free-form `category` column on the `places` table.  This mapping lets us
# translate between the two worlds.

INTEREST_TO_DB_CATEGORIES: Dict[str, List[str]] = {
    "Food and Beverage": ["restaurant", "cafe", "bakery", "brewery", "food", "bar"],
    "Entertainment": ["entertainment", "shopping", "nightlife", "casino", "spa"],
    "Culture and History": ["museum", "gallery", "church", "historic", "tourism", "culture"],
    "Sport": ["sport", "stadium", "golf", "recreation"],
    "Natural Place": ["park", "garden", "nature", "beach", "trail", "island"],
}


class VenueService:
    """Read-only access to the Airflow venue database."""

    def __init__(self, db_url: Optional[str] = None):
        url = db_url or settings.APP_DB_URL
        self._engine = create_engine(url, pool_pre_ping=True, pool_size=3)
        self._Session = sessionmaker(bind=self._engine)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_venues_for_itinerary(
        self,
        city: str,
        interests: List[str],
        budget_per_day: float,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Return venue rows from the Airflow DB that match the traveller's
        city and interests.  Results are meant to be injected into the
        Gemini itinerary-generation prompt so the AI uses *real* venues.

        Args:
            city: Target city (e.g. "Toronto").
            interests: List of canonical interest names from NLP extraction.
            budget_per_day: Daily budget — used for informational ordering only.
            limit: Max rows to return.

        Returns:
            List of dicts with keys: place_id, name, category, address,
            phone, hours, description, source_url.
        """
        db_cats = self._expand_interests(interests)

        session = self._Session()
        try:
            # Build a simple query against the places table.
            # Filter by city (case-insensitive ILIKE) and category.
            query = text("""
                SELECT
                    id        AS place_id,
                    name,
                    category,
                    address,
                    phone,
                    hours,
                    description,
                    source_url
                FROM places
                WHERE LOWER(city) LIKE :city_pattern
                  AND LOWER(category) = ANY(:categories)
                ORDER BY last_updated_at DESC
                LIMIT :lim
            """)

            rows = session.execute(
                query,
                {
                    "city_pattern": f"%{city.lower()}%",
                    "categories": [c.lower() for c in db_cats],
                    "lim": limit,
                },
            ).fetchall()

            return [dict(r._mapping) for r in rows]
        except Exception:
            logger.warning("Venue DB query failed — returning empty list", exc_info=True)
            return []
        finally:
            session.close()

    def get_all_venues_for_city(
        self,
        city: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return all active venues for a city regardless of category."""
        session = self._Session()
        try:
            query = text("""
                SELECT
                    id        AS place_id,
                    name,
                    category,
                    address,
                    phone,
                    hours,
                    description,
                    source_url
                FROM places
                WHERE LOWER(city) LIKE :city_pattern
                ORDER BY last_updated_at DESC
                LIMIT :lim
            """)
            rows = session.execute(
                query,
                {"city_pattern": f"%{city.lower()}%", "lim": limit},
            ).fetchall()
            return [dict(r._mapping) for r in rows]
        except Exception:
            logger.warning("Venue DB query failed — returning empty list", exc_info=True)
            return []
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _expand_interests(interests: List[str]) -> List[str]:
        """Map NLP interest names to a flat list of DB category values."""
        cats: List[str] = []
        for interest in interests:
            mapped = INTEREST_TO_DB_CATEGORIES.get(interest, [])
            if mapped:
                cats.extend(mapped)
            else:
                # Fall back to interest name itself
                cats.append(interest.lower())
        return list(set(cats))

    @staticmethod
    def format_venues_for_prompt(venues: List[Dict[str, Any]]) -> str:
        """
        Format venue rows into a text block suitable for inclusion in
        a Gemini prompt so the AI knows about *real* places.
        """
        if not venues:
            return "(No venue data available from the database.)"

        lines = ["## Available Venues (from database)\n"]
        for v in venues:
            name = v.get("name") or "Unknown"
            cat = v.get("category") or ""
            addr = v.get("address") or ""
            hours = v.get("hours") or ""
            desc = (v.get("description") or "")[:200]
            line = f"- **{name}** [{cat}] — {addr}"
            if hours:
                line += f" | Hours: {hours}"
            if desc:
                line += f" | {desc}"
            lines.append(line)
        return "\n".join(lines)
