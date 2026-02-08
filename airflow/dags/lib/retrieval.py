from __future__ import annotations
from typing import Any, Dict, List, Optional

from lib.chroma_index import query_places
from lib.db import Place, get_session, init_db

def retrieve_places(
    query: str,
    top_k: int = 10,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    init_db()

    where = {}
    if category:
        where["category"] = category

    hits = query_places(query_text=query, top_k=top_k, where=where)

    # Deduplicate by place_id (multiple chunks may come back)
    place_ids = []
    seen = set()
    for h in hits:
        pid = h.get("place_id")
        if pid and pid not in seen:
            seen.add(pid)
            place_ids.append(pid)

    session = get_session()
    try:
        places = session.query(Place).filter(Place.id.in_(place_ids)).all()
        by_id = {p.id: p for p in places}

        out: List[Dict[str, Any]] = []
        for h in hits:
            pid = h.get("place_id")
            p = by_id.get(pid)
            if not p:
                continue

            out.append(
                {
                    "place_id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "address": p.address,
                    "phone": p.phone,
                    "hours": p.hours,
                    "description": p.description,
                    "source_url": p.source_url,
                    # citation/debug
                    "match_distance": h["distance"],
                    "matched_chunk": h["document"],
                }
            )
        return out
    finally:
        session.close()
