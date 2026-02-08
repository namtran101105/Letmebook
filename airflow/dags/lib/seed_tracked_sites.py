from __future__ import annotations

import hashlib
import json
from sqlalchemy import text

from lib.db import get_engine, init_db

PLACES = [
    {"place_key": "visit_1000_islands", "canonical_name": "Visit 1000 Islands", "city": "Kingston/Brockville", "category": "tourism"},

    {"place_key": "cn_tower", "canonical_name": "CN Tower", "city": "Toronto", "category": "tourism"},
    {"place_key": "toronto_islands_ferry", "canonical_name": "Toronto Islands Ferry", "city": "Toronto", "category": "island"},
    {"place_key": "yorkdale_shopping_centre", "canonical_name": "Yorkdale Shopping Centre", "city": "Toronto", "category": "shopping"},
    {"place_key": "rogers_centre", "canonical_name": "Rogers Centre", "city": "Toronto", "category": "sport"},
    {"place_key": "happy_lamb_hot_pot", "canonical_name": "Happy Lamb Hot Pot", "city": "Toronto", "category": "restaurant"},
    {"place_key": "royal_ontario_museum", "canonical_name": "Royal Ontario Museum", "city": "Toronto", "category": "museum"},
    {"place_key": "art_gallery_ontario", "canonical_name": "Art Gallery of Ontario", "city": "Toronto", "category": "gallery"},
    {"place_key": "earl_bales_ski_centre", "canonical_name": "Earl Bales Ski and Snowboard Centre", "city": "Toronto", "category": "recreation"},
    {"place_key": "cong_ca_phe_toronto", "canonical_name": "Cong Ca Phe Toronto", "city": "Toronto", "category": "cafe"},
    {"place_key": "toronto_eaton_centre", "canonical_name": "CF Toronto Eaton Centre", "city": "Toronto", "category": "shopping"},
    {"place_key": "st_lawrence_market", "canonical_name": "St. Lawrence Market", "city": "Toronto", "category": "food"},
    {"place_key": "ripleys_aquarium_canada", "canonical_name": "Ripley's Aquarium of Canada", "city": "Toronto", "category": "entertainment"},
    {"place_key": "casa_loma", "canonical_name": "Casa Loma", "city": "Toronto", "category": "historic"},
    {"place_key": "toronto_zoo", "canonical_name": "Toronto Zoo", "city": "Toronto", "category": "park"},
    {"place_key": "ontario_science_centre", "canonical_name": "Ontario Science Centre", "city": "Toronto", "category": "museum"},
    {"place_key": "distillery_district", "canonical_name": "Distillery Historic District", "city": "Toronto", "category": "historic"},
    {"place_key": "high_park", "canonical_name": "High Park", "city": "Toronto", "category": "park"},
    {"place_key": "nathan_phillips_square", "canonical_name": "Nathan Phillips Square", "city": "Toronto", "category": "entertainment"},
    {"place_key": "scotiabank_arena", "canonical_name": "Scotiabank Arena", "city": "Toronto", "category": "sport"},
    {"place_key": "toronto_symphony_orchestra", "canonical_name": "Toronto Symphony Orchestra", "city": "Toronto", "category": "entertainment"},
    {"place_key": "kensington_market", "canonical_name": "Kensington Market", "city": "Toronto", "category": "food"},
    {"place_key": "rec_room_toronto", "canonical_name": "The Rec Room Toronto Roundhouse", "city": "Toronto", "category": "entertainment"},
    {"place_key": "steam_whistle_brewery", "canonical_name": "Steam Whistle Brewery", "city": "Toronto", "category": "brewery"},
    {"place_key": "aga_khan_museum", "canonical_name": "Aga Khan Museum", "city": "Toronto", "category": "museum"},
    {"place_key": "harbourfront_centre", "canonical_name": "Harbourfront Centre", "city": "Toronto", "category": "entertainment"},
    {"place_key": "allan_gardens_conservatory", "canonical_name": "Allan Gardens Conservatory", "city": "Toronto", "category": "garden"},
]


PAGES = [
    {
        "place_key": "visit_1000_islands",
        "url": "https://visit1000islands.com/",
        "page_type": "overview",
        "extract_strategy": "jsonld",
        "css_rules": None,
        "enabled": True,
    },

    {"place_key": "cn_tower", "url": "https://www.cntower.ca/plan-your-visit/tickets-and-hours/tickets", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "cn_tower", "url": "https://www.cntower.ca/plan-your-visit/tickets-and-hours/hours", "page_type": "hours", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "toronto_islands_ferry", "url": "https://www.toronto.ca/explore-enjoy/parks-recreation/places-spaces/beaches-gardens-attractions/toronto-island-park/all-ferry-schedules/", "page_type": "schedule", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "yorkdale_shopping_centre", "url": "https://yorkdale.com/", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "rogers_centre", "url": "https://www.ticketmaster.ca/rogers-centre-tickets-toronto/venue/131114", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "happy_lamb_hot_pot", "url": "https://happylambhotpotca.com/menu.html", "page_type": "menu", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "royal_ontario_museum", "url": "https://tickets.rom.on.ca/en/shop", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "royal_ontario_museum", "url": "https://www.rom.on.ca/visit/visitor-information", "page_type": "hours", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "art_gallery_ontario", "url": "https://ago.ca/visit/location-hours-admission", "page_type": "hours", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "art_gallery_ontario", "url": "https://visit.ago.ca/56644/58933", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "earl_bales_ski_centre", "url": "https://www.toronto.ca/explore-enjoy/parks-recreation/places-spaces/parks-and-recreation-facilities/location/?id=2766&title=Earl-Bales-Ski-and-Snowboard-Centre", "page_type": "hours", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "earl_bales_ski_centre", "url": "https://www.toronto.ca/explore-enjoy/parks-recreation/program-activities/ice-snow-activities/downhill-skiing-snowboarding-centres/", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "cong_ca_phe_toronto", "url": "https://congcaphe.ca/menu/#heading__food", "page_type": "menu", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "toronto_eaton_centre", "url": "https://shops.cadillacfairview.com/property/cf-toronto-eaton-centre", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "st_lawrence_market", "url": "https://www.stlawrencemarket.com/", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "ripleys_aquarium_canada", "url": "https://www.ripleyaquariums.com/canada/buy-tickets/", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "ripleys_aquarium_canada", "url": "https://www.ripleyaquariums.com/canada/hours/", "page_type": "hours", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "casa_loma", "url": "https://casaloma.ca/project/admission/", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "casa_loma", "url": "https://casaloma.ca/", "page_type": "hours", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "toronto_zoo", "url": "https://www.torontozoo.com/tickets", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "toronto_zoo", "url": "https://www.torontozoo.com/hours", "page_type": "hours", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "ontario_science_centre", "url": "https://www.ontariosciencecentre.ca/visit", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "distillery_district", "url": "https://www.thedistillerydistrict.com/", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "high_park", "url": "https://www.toronto.ca/data/parks/prd/facilities/complex/108/index.html", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "nathan_phillips_square", "url": "https://www.toronto.ca/data/parks/prd/facilities/complex/1/index.html", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "scotiabank_arena", "url": "https://www.ticketmaster.ca/scotiabank-arena-tickets-toronto/venue/131080", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "toronto_symphony_orchestra", "url": "https://www.tso.ca/concerts-and-events/", "page_type": "tickets", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "kensington_market", "url": "https://kensingtonmarket.to/", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "rec_room_toronto", "url": "https://www.therecroom.com/toronto-roundhouse", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "steam_whistle_brewery", "url": "https://steamwhistle.ca/pages/brewery-tours", "page_type": "tours", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "aga_khan_museum", "url": "https://agakhanmuseum.org/visit/tickets-hours.html", "page_type": "tickets_hours", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "harbourfront_centre", "url": "https://harbourfrontcentre.com/", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},

    {"place_key": "allan_gardens_conservatory", "url": "https://www.toronto.ca/data/parks/prd/facilities/complex/27/index.html", "page_type": "hours", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
]


def stable_hash(obj) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    init_db()
    eng = get_engine()

    # satisfies legacy NOT NULL content_json
    empty_content = {}
    empty_hash = stable_hash(empty_content)

    # NOTE: for text() queries, pass JSON as string and CAST to jsonb
    upsert_place_stmt = text(
        """
        INSERT INTO places (
          place_key, canonical_name, name, city, category,
          profile_json,
          content_json, content_hash
        )
        VALUES (
          :place_key, :canonical_name, :canonical_name, :city, :category,
          COALESCE(CAST(:profile_json AS jsonb), '{}'::jsonb),
          COALESCE(CAST(:content_json AS jsonb), '{}'::jsonb),
          COALESCE(:content_hash, :fallback_hash)
        )
        ON CONFLICT (place_key) DO UPDATE SET
          canonical_name = EXCLUDED.canonical_name,
          name = EXCLUDED.name,
          city = EXCLUDED.city,
          category = EXCLUDED.category,
          profile_json = EXCLUDED.profile_json,
          content_json = EXCLUDED.content_json,
          content_hash = EXCLUDED.content_hash
        RETURNING id
        """
    )

    upsert_page_stmt = text(
        """
        INSERT INTO tracked_pages (place_id, url, page_type, extract_strategy, css_rules, enabled)
        VALUES (
          :place_id, :url, :page_type, :extract_strategy,
          CAST(:css_rules AS jsonb),
          :enabled
        )
        ON CONFLICT (url) DO UPDATE SET
          place_id = EXCLUDED.place_id,
          page_type = EXCLUDED.page_type,
          extract_strategy = EXCLUDED.extract_strategy,
          css_rules = EXCLUDED.css_rules,
          enabled = EXCLUDED.enabled
        """
    )

    with eng.begin() as conn:
        place_id_by_key = {}

        # 1) Upsert places
        for p in PLACES:
            params = {
                **p,
                # must be JSON strings for psycopg2 + text() query
                "profile_json": json.dumps({}, ensure_ascii=False),
                "content_json": json.dumps(empty_content, ensure_ascii=False),
                "content_hash": empty_hash,
                "fallback_hash": empty_hash,
            }
            place_id = conn.execute(upsert_place_stmt, params).scalar_one()
            place_id_by_key[p["place_key"]] = place_id
            print(f"Upsert place {p['place_key']} -> id={place_id}")

        # 2) Upsert pages
        for pg in PAGES:
            place_id = place_id_by_key[pg["place_key"]]

            css_rules_json = (
                json.dumps(pg["css_rules"], ensure_ascii=False)
                if pg.get("css_rules") is not None
                else None
            )

            conn.execute(
                upsert_page_stmt,
                {
                    "place_id": place_id,
                    "url": pg["url"],
                    "page_type": pg["page_type"],
                    "extract_strategy": pg["extract_strategy"],
                    "css_rules": css_rules_json,  # JSON string or None
                    "enabled": bool(pg.get("enabled", True)),
                },
            )
            print(f"Upsert page {pg['url']} -> place_id={place_id}")

    print("Done. ✅ Seeded places + tracked_pages.")


if __name__ == "__main__":
    main()
