"""
Data models for trip preferences extracted from user input.
"""
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime
import json


@dataclass
class TripPreferences:
    """Structured trip preferences extracted from natural language."""

    # City and country preferences
    city: Optional[str] = None
    country: Optional[str] = None

    # Travel dates
    start_date: Optional[str] = None  # Format: YYYY-MM-DD
    end_date: Optional[str] = None    # Format: YYYY-MM-DD
    duration_days: Optional[int] = None

    # Interests and preferences
    interests: List[str] = None  # Categorized into: Food and Beverage, Entertainment, Culture and History, Sport, Natural Place
    pace: Optional[str] = None  # "relaxed", "moderate", or "packed"

    # Drop off or location of stay
    location_preference: Optional[str] = None  # e.g., "downtown", "near nature", "historic district"

    # Booking preferences
    needs_flight: Optional[bool] = None   # True = wants flight booking, False = no, None = not asked yet
    needs_airbnb: Optional[bool] = None   # True = wants Airbnb booking, False = no, None = not asked yet
    source_location: Optional[str] = None  # Where user is traveling from (only needed if needs_flight is True)

    # Pace synonym mapping → canonical values
    PACE_SYNONYMS = {
        # relaxed synonyms
        "relax": "relaxed", "relaxed": "relaxed", "relaxing": "relaxed",
        "chill": "relaxed", "chilled": "relaxed", "chilling": "relaxed",
        "slow": "relaxed", "lazy": "relaxed", "leisurely": "relaxed",
        "easy": "relaxed", "easygoing": "relaxed", "casual": "relaxed",
        "laid-back": "relaxed", "laid back": "relaxed", "laidback": "relaxed",
        # moderate synonyms
        "moderate": "moderate", "medium": "moderate", "balanced": "moderate",
        "normal": "moderate", "average": "moderate", "steady": "moderate",
        # packed synonyms
        "packed": "packed", "fast": "packed", "rush": "packed",
        "rushed": "packed", "busy": "packed", "intense": "packed",
        "active": "packed", "aggressive": "packed", "rapid": "packed",
        "hectic": "packed", "jam-packed": "packed", "jam packed": "packed",
        "full": "packed", "non-stop": "packed", "nonstop": "packed",
    }

    # Words that indicate pace, not interests
    PACE_WORDS = set(PACE_SYNONYMS.keys())

    # The 5 canonical interest categories
    VALID_CATEGORIES = {
        "Food and Beverage",
        "Entertainment",
        "Culture and History",
        "Sport",
        "Natural Place",
    }

    # Keyword → category mapping for normalization
    INTEREST_KEYWORDS = {
        # Food and Beverage
        "food": "Food and Beverage", "beverage": "Food and Beverage",
        "food tour": "Food and Beverage", "food tours": "Food and Beverage",
        "restaurant": "Food and Beverage", "restaurants": "Food and Beverage",
        "dining": "Food and Beverage", "eat": "Food and Beverage",
        "eating": "Food and Beverage", "cuisine": "Food and Beverage",
        "coffee": "Food and Beverage", "cafe": "Food and Beverage",
        "bakery": "Food and Beverage", "brewery": "Food and Beverage",
        "winery": "Food and Beverage", "wine": "Food and Beverage",
        "beer": "Food and Beverage", "cocktail": "Food and Beverage",
        "cocktails": "Food and Beverage", "drink": "Food and Beverage",
        "drinks": "Food and Beverage", "street food": "Food and Beverage",
        "cooking": "Food and Beverage", "brunch": "Food and Beverage",
        "breakfast": "Food and Beverage", "lunch": "Food and Beverage",
        "dinner": "Food and Beverage", "dessert": "Food and Beverage",
        "tasting": "Food and Beverage", "foodie": "Food and Beverage",
        "culinary": "Food and Beverage", "local food": "Food and Beverage",
        "tea": "Food and Beverage", "distillery": "Food and Beverage",
        # Entertainment
        "entertainment": "Entertainment", "shopping": "Entertainment",
        "casino": "Entertainment", "spa": "Entertainment",
        "bar": "Entertainment", "bars": "Entertainment",
        "pub": "Entertainment", "pubs": "Entertainment",
        "arcade": "Entertainment", "nightlife": "Entertainment",
        "club": "Entertainment", "clubs": "Entertainment",
        "nightclub": "Entertainment", "karaoke": "Entertainment",
        "cinema": "Entertainment", "movie": "Entertainment",
        "movies": "Entertainment", "theater": "Entertainment",
        "theatre": "Entertainment", "concert": "Entertainment",
        "concerts": "Entertainment", "live music": "Entertainment",
        "music": "Entertainment", "festival": "Entertainment",
        "festivals": "Entertainment", "amusement park": "Entertainment",
        "theme park": "Entertainment", "waterpark": "Entertainment",
        "bowling": "Entertainment", "escape room": "Entertainment",
        "zoo": "Entertainment", "aquarium": "Entertainment",
        "mall": "Entertainment", "market": "Entertainment",
        "markets": "Entertainment", "massage": "Entertainment",
        "wellness": "Entertainment", "yoga": "Entertainment",
        # Culture and History
        "culture": "Culture and History", "history": "Culture and History",
        "museum": "Culture and History", "museums": "Culture and History",
        "library": "Culture and History", "libraries": "Culture and History",
        "church": "Culture and History", "churches": "Culture and History",
        "cathedral": "Culture and History", "temple": "Culture and History",
        "mosque": "Culture and History", "pyramid": "Culture and History",
        "pyramids": "Culture and History", "old quarter": "Culture and History",
        "old quarters": "Culture and History", "old town": "Culture and History",
        "fortress": "Culture and History", "castle": "Culture and History",
        "castles": "Culture and History", "palace": "Culture and History",
        "palaces": "Culture and History", "monument": "Culture and History",
        "monuments": "Culture and History", "heritage": "Culture and History",
        "historic": "Culture and History", "historical": "Culture and History",
        "ruins": "Culture and History", "archaeology": "Culture and History",
        "art": "Culture and History", "art gallery": "Culture and History",
        "gallery": "Culture and History", "galleries": "Culture and History",
        "architecture": "Culture and History", "landmark": "Culture and History",
        "landmarks": "Culture and History", "memorial": "Culture and History",
        "fort": "Culture and History", "sightseeing": "Culture and History",
        "sight seeing": "Culture and History", "tour": "Culture and History",
        "tours": "Culture and History", "cultural": "Culture and History",
        # Sport
        "sport": "Sport", "sports": "Sport",
        "soccer": "Sport", "football": "Sport",
        "basketball": "Sport", "nfl": "Sport",
        "nba": "Sport", "nhl": "Sport",
        "mlb": "Sport", "baseball": "Sport",
        "hockey": "Sport", "tennis": "Sport",
        "golf": "Sport", "stadium": "Sport",
        "stadiums": "Sport", "arena": "Sport",
        "gym": "Sport", "fitness": "Sport",
        "surfing": "Sport", "skiing": "Sport",
        "snowboarding": "Sport", "skating": "Sport",
        "cycling": "Sport", "biking": "Sport",
        "running": "Sport", "marathon": "Sport",
        "rugby": "Sport", "cricket": "Sport",
        "boxing": "Sport", "mma": "Sport",
        "volleyball": "Sport", "swimming": "Sport",
        "kayaking": "Sport", "canoeing": "Sport",
        "rock climbing": "Sport", "climbing": "Sport",
        # Natural Place
        "nature": "Natural Place", "natural": "Natural Place",
        "national park": "Natural Place", "park": "Natural Place",
        "parks": "Natural Place", "beach": "Natural Place",
        "beaches": "Natural Place", "sea": "Natural Place",
        "ocean": "Natural Place", "lake": "Natural Place",
        "lakes": "Natural Place", "river": "Natural Place",
        "rivers": "Natural Place", "fishing": "Natural Place",
        "diving": "Natural Place", "scuba": "Natural Place",
        "snorkeling": "Natural Place", "trekking": "Natural Place",
        "hiking": "Natural Place", "hike": "Natural Place",
        "trail": "Natural Place", "trails": "Natural Place",
        "mountain": "Natural Place", "mountains": "Natural Place",
        "forest": "Natural Place", "jungle": "Natural Place",
        "waterfall": "Natural Place", "waterfalls": "Natural Place",
        "garden": "Natural Place", "gardens": "Natural Place",
        "botanical": "Natural Place", "wildlife": "Natural Place",
        "safari": "Natural Place", "bird watching": "Natural Place",
        "camping": "Natural Place", "outdoors": "Natural Place",
        "outdoor": "Natural Place", "scenic": "Natural Place",
        "island": "Natural Place", "islands": "Natural Place",
        "cave": "Natural Place", "caves": "Natural Place",
        "canyon": "Natural Place", "valley": "Natural Place",
        "waterfront": "Natural Place", "countryside": "Natural Place",
    }

    def __post_init__(self):
        """Initialize empty lists, normalize pace, and categorize interests."""
        if self.interests is None:
            self.interests = []

        # Normalize pace using synonym mapping
        self.pace = self._normalize_pace(self.pace)

        # Filter pace-related words out of interests
        self._filter_pace_from_interests()

        # Categorize interests into the 5 canonical categories
        self._categorize_interests()

    def _normalize_pace(self, pace: Optional[str]) -> Optional[str]:
        """Normalize pace value using synonym mapping."""
        if not pace:
            return pace
        return self.PACE_SYNONYMS.get(pace.strip().lower(), pace)

    def _filter_pace_from_interests(self):
        """Remove pace-related words from interests and set pace if not already set."""
        if not self.interests:
            return
        cleaned = []
        for interest in self.interests:
            normalized = interest.strip().lower()
            if normalized in self.PACE_WORDS:
                # If pace isn't set yet, use this as pace
                if not self.pace:
                    self.pace = self.PACE_SYNONYMS[normalized]
            else:
                cleaned.append(interest)
        self.interests = cleaned

    def _categorize_interests(self):
        """Map raw interest keywords to the 5 canonical categories (deduplicated)."""
        if not self.interests:
            return
        categories = set()
        for interest in self.interests:
            normalized = interest.strip().lower()
            # Check if it's already a valid category name
            if interest in self.VALID_CATEGORIES:
                categories.add(interest)
                continue
            # Try exact keyword match
            if normalized in self.INTEREST_KEYWORDS:
                categories.add(self.INTEREST_KEYWORDS[normalized])
                continue
            # Try substring match — check if any keyword appears in the interest
            matched = False
            for keyword, category in self.INTEREST_KEYWORDS.items():
                if keyword in normalized or normalized in keyword:
                    categories.add(category)
                    matched = True
                    break
            # If no match found, skip it (don't include uncategorized items)
        self.interests = sorted(categories)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> 'TripPreferences':
        """Create instance from dictionary, ignoring unknown fields."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def from_json(cls, json_str: str) -> 'TripPreferences':
        """Create instance from JSON string."""
        return cls.from_dict(json.loads(json_str))
