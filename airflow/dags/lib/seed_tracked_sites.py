from __future__ import annotations

import hashlib
import json
from sqlalchemy import text

from lib.db import get_engine, init_db

PLACES = [
    # --- Kingston / Brockville ---
    {
        "place_key": "visit_1000_islands",
        "canonical_name": "Visit 1000 Islands",
        "city": "Kingston/Brockville",
        "category": "tourism",
    },
    # --- Toronto ---
    {
        "place_key": "cn_tower",
        "canonical_name": "CN Tower",
        "city": "Toronto",
        "category": "tourism",
    },
    {
        "place_key": "rom",
        "canonical_name": "Royal Ontario Museum",
        "city": "Toronto",
        "category": "museum",
    },
    {
        "place_key": "st_lawrence_market",
        "canonical_name": "St. Lawrence Market",
        "city": "Toronto",
        "category": "food",
    },
    {
        "place_key": "ripley_aquarium",
        "canonical_name": "Ripley's Aquarium of Canada",
        "city": "Toronto",
        "category": "entertainment",
    },
    {
        "place_key": "high_park",
        "canonical_name": "High Park",
        "city": "Toronto",
        "category": "park",
    },
    {
        "place_key": "distillery_district",
        "canonical_name": "Distillery Historic District",
        "city": "Toronto",
        "category": "culture",
    },
    {
        "place_key": "kensington_market",
        "canonical_name": "Kensington Market",
        "city": "Toronto",
        "category": "food",
    },
    {
        "place_key": "hockey_hall_of_fame",
        "canonical_name": "Hockey Hall of Fame",
        "city": "Toronto",
        "category": "sport",
    },
    {
        "place_key": "casa_loma",
        "canonical_name": "Casa Loma",
        "city": "Toronto",
        "category": "culture",
    },
    {
        "place_key": "ago",
        "canonical_name": "Art Gallery of Ontario",
        "city": "Toronto",
        "category": "museum",
    },
    {
        "place_key": "toronto_islands",
        "canonical_name": "Toronto Islands",
        "city": "Toronto",
        "category": "park",
    },
    {
        "place_key": "harbourfront_centre",
        "canonical_name": "Harbourfront Centre",
        "city": "Toronto",
        "category": "entertainment",
    },
    {
        "place_key": "bata_shoe_museum",
        "canonical_name": "Bata Shoe Museum",
        "city": "Toronto",
        "category": "museum",
    },
    {
        "place_key": "toronto_zoo",
        "canonical_name": "Toronto Zoo",
        "city": "Toronto",
        "category": "entertainment",
    },
    {
        "place_key": "aga_khan_museum",
        "canonical_name": "Aga Khan Museum",
        "city": "Toronto",
        "category": "museum",
    },
]

PAGES = [
    # --- Kingston / Brockville ---
    {
        "place_key": "visit_1000_islands",
        "url": "https://visit1000islands.com/",
        "page_type": "overview",
        "extract_strategy": "jsonld",
        "css_rules": None,
        "enabled": True,
    },
    # --- Toronto ---
    {"place_key": "cn_tower", "url": "https://www.cntower.ca", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "rom", "url": "https://www.rom.on.ca", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "st_lawrence_market", "url": "https://www.stlawrencemarket.com", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "ripley_aquarium", "url": "https://www.ripleyaquariums.com/canada", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "high_park", "url": "https://www.highparktoronto.com", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "distillery_district", "url": "https://www.thedistillerydistrict.com", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "kensington_market", "url": "https://www.kensingtonmarket.ca", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "hockey_hall_of_fame", "url": "https://www.hhof.com", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "casa_loma", "url": "https://casaloma.ca", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "ago", "url": "https://ago.ca", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "toronto_islands", "url": "https://www.toronto.ca/explore-enjoy/parks-gardens-beaches/toronto-islands", "page_type": "overview", "extract_strategy": "text", "css_rules": None, "enabled": True},
    {"place_key": "harbourfront_centre", "url": "https://www.harbourfrontcentre.com", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "bata_shoe_museum", "url": "https://www.batashoemuseum.ca", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "toronto_zoo", "url": "https://www.torontozoo.com", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
    {"place_key": "aga_khan_museum", "url": "https://www.agakhanmuseum.org", "page_type": "overview", "extract_strategy": "jsonld", "css_rules": None, "enabled": True},
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
          place_key, canonical_name, city, category,
          profile_json,
          content_json, content_hash
        )
        VALUES (
          :place_key, :canonical_name, :city, :category,
          COALESCE(CAST(:profile_json AS jsonb), '{}'::jsonb),
          COALESCE(CAST(:content_json AS jsonb), '{}'::jsonb),
          COALESCE(:content_hash, :fallback_hash)
        )
        ON CONFLICT (place_key) DO UPDATE SET
          canonical_name = EXCLUDED.canonical_name,
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
