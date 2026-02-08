"""
Venue service — queries the Airflow-managed PostgreSQL database for place/venue
data that was scraped and stored by the website_change_monitor DAG.

The FastAPI backend reads from the *same* database that Airflow writes to.
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
# Toronto fallback venue list — used when the DB is unreachable so the demo
# always works.  Each dict mirrors the columns returned by get_venues_*.
# ---------------------------------------------------------------------------
TORONTO_FALLBACK_VENUES: List[Dict[str, Any]] = [
    {
        "place_key": "cn_tower",
        "name": "CN Tower",
        "category": "tourism",
        "address": "290 Bremner Blvd, Toronto, ON M5V 3L9",
        "description": "Iconic 553-metre communications and observation tower with glass floor and revolving restaurant.",
        "source_url": "https://www.cntower.ca",
    },
    {
        "place_key": "rom",
        "name": "Royal Ontario Museum",
        "category": "museum",
        "address": "100 Queens Park, Toronto, ON M5S 2C6",
        "description": "Canada's largest museum of world cultures and natural history.",
        "source_url": "https://www.rom.on.ca",
    },
    {
        "place_key": "st_lawrence_market",
        "name": "St. Lawrence Market",
        "category": "food",
        "address": "93 Front St E, Toronto, ON M5E 1C3",
        "description": "Historic public market with over 120 vendors offering fresh produce, specialty foods, and artisan goods.",
        "source_url": "https://www.stlawrencemarket.com",
    },
    {
        "place_key": "ripley_aquarium",
        "name": "Ripley's Aquarium of Canada",
        "category": "entertainment",
        "address": "288 Bremner Blvd, Toronto, ON M5V 3L9",
        "description": "Marine aquarium with underwater tunnel, touch tanks, and over 20,000 aquatic animals.",
        "source_url": "https://www.ripleyaquariums.com/canada",
    },
    {
        "place_key": "high_park",
        "name": "High Park",
        "category": "park",
        "address": "1873 Bloor St W, Toronto, ON M6R 2Z3",
        "description": "Large urban park with nature trails, a zoo, sports facilities, and beautiful gardens.",
        "source_url": "https://www.highparktoronto.com",
    },
    {
        "place_key": "distillery_district",
        "name": "Distillery Historic District",
        "category": "culture",
        "address": "55 Mill St, Toronto, ON M5A 3C4",
        "description": "Pedestrian-only village of Victorian industrial architecture with galleries, boutiques, and restaurants.",
        "source_url": "https://www.thedistillerydistrict.com",
    },
    {
        "place_key": "kensington_market",
        "name": "Kensington Market",
        "category": "food",
        "address": "Kensington Ave, Toronto, ON M5T 2K2",
        "description": "Bohemian neighbourhood with vintage shops, diverse food stalls, and vibrant street art.",
        "source_url": "https://www.kensingtonmarket.ca",
    },
    {
        "place_key": "hockey_hall_of_fame",
        "name": "Hockey Hall of Fame",
        "category": "sport",
        "address": "30 Yonge St, Toronto, ON M5E 1X8",
        "description": "Museum dedicated to the history of ice hockey with interactive exhibits and the Stanley Cup.",
        "source_url": "https://www.hhof.com",
    },
    {
        "place_key": "casa_loma",
        "name": "Casa Loma",
        "category": "culture",
        "address": "1 Austin Terrace, Toronto, ON M5R 1X8",
        "description": "Gothic Revival castle with decorated suites, towers, gardens, and an 800-foot underground tunnel.",
        "source_url": "https://casaloma.ca",
    },
    {
        "place_key": "ago",
        "name": "Art Gallery of Ontario",
        "category": "museum",
        "address": "317 Dundas St W, Toronto, ON M5T 1G4",
        "description": "One of the largest art museums in North America with a collection spanning from the first century to the present.",
        "source_url": "https://ago.ca",
    },
    {
        "place_key": "toronto_islands",
        "name": "Toronto Islands",
        "category": "park",
        "address": "Toronto Islands, Toronto, ON",
        "description": "Chain of small islands offering beaches, picnic areas, bike rentals, and skyline views.",
        "source_url": "https://www.toronto.ca/explore-enjoy/parks-gardens-beaches/toronto-islands",
    },
    {
        "place_key": "harbourfront_centre",
        "name": "Harbourfront Centre",
        "category": "entertainment",
        "address": "235 Queens Quay W, Toronto, ON M5J 2G8",
        "description": "Cultural centre on the waterfront with year-round festivals, art exhibitions, and performances.",
        "source_url": "https://www.harbourfrontcentre.com",
    },
    {
        "place_key": "bata_shoe_museum",
        "name": "Bata Shoe Museum",
        "category": "museum",
        "address": "327 Bloor St W, Toronto, ON M5S 1W7",
        "description": "Unique museum housing a collection of over 13,000 shoes spanning 4,500 years of history.",
        "source_url": "https://www.batashoemuseum.ca",
    },
    {
        "place_key": "toronto_zoo",
        "name": "Toronto Zoo",
        "category": "entertainment",
        "address": "2000 Meadowvale Rd, Toronto, ON M1B 5K7",
        "description": "Large zoo with over 5,000 animals representing 450+ species across themed geographic regions.",
        "source_url": "https://www.torontozoo.com",
    },
    {
        "place_key": "aga_khan_museum",
        "name": "Aga Khan Museum",
        "category": "museum",
        "address": "77 Wynford Dr, Toronto, ON M3C 1K1",
        "description": "Museum showcasing Islamic art and Muslim civilisations with concerts, films, and lectures.",
        "source_url": "https://www.agakhanmuseum.org",
    },
]

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
        try:
            self._engine = create_engine(url, pool_pre_ping=True, pool_size=3)
            self._Session = sessionmaker(bind=self._engine)
            self._db_available = True
        except Exception:
            logger.warning("Could not create DB engine — will use fallback venues")
            self._db_available = False
            self._engine = None
            self._Session = None

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
        itinerary-generation prompt so the AI uses *real* venues.

        Args:
            city: Target city (e.g. "Toronto").
            interests: List of canonical interest names from NLP extraction.
            budget_per_day: Daily budget — used for informational ordering only.
            limit: Max rows to return.

        Returns:
            List of dicts with keys: place_id, name, category, address,
            phone, hours, description, source_url.
        """
        if not self._db_available:
            return []

        db_cats = self._expand_interests(interests)

        session = self._Session()
        try:
            # Build a simple query against the places table.
            # Filter by city (case-insensitive ILIKE) and category.
            query = text("""
                SELECT
                    id        AS place_id,
                    place_key,
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
        if not self._db_available:
            return []

        session = self._Session()
        try:
            query = text("""
                SELECT
                    id        AS place_id,
                    place_key,
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

    def get_toronto_venues(self) -> List[Dict[str, Any]]:
        """
        Return Toronto venue list for the conversational chat flow.

        Tries the DB first; falls back to ``TORONTO_FALLBACK_VENUES`` if the
        DB is unreachable or returns no rows.
        """
        venues = self.get_all_venues_for_city("Toronto")
        if venues:
            return venues
        logger.info("Using Toronto fallback venue list (DB empty or unreachable)")
        return list(TORONTO_FALLBACK_VENUES)  # return a copy

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

    @staticmethod
    def format_venues_for_chat(venues: List[Dict[str, Any]]) -> str:
        """
        Format venues with ``place_key`` and ``source_url`` so the LLM can
        produce ``Source: {venue_id}, {url}`` citations in the itinerary.
        """
        if not venues:
            return "(No venues available.)"

        lines: List[str] = []
        for v in venues:
            vid = v.get("place_key") or v.get("place_id") or "unknown"
            name = v.get("name") or v.get("canonical_name") or "Unknown"
            cat = v.get("category") or ""
            addr = v.get("address") or ""
            url = v.get("source_url") or ""
            desc = (v.get("description") or "")[:200]
            line = f"[venue_id: {vid}] {name} [{cat}] — {addr}"
            if url:
                line += f" | URL: {url}"
            if desc:
                line += f" | {desc}"
            lines.append(line)
        return "\n".join(lines)
