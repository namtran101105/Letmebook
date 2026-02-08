from __future__ import annotations

import hashlib
import json
import os
import re
import math
import random
from typing import Any, Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from .db import ChangeEvent, Place, PlaceSnapshot, TrackedSite, get_session, init_db

DEFAULT_TIMEOUT = int(os.getenv("FETCH_TIMEOUT_SECONDS", "20"))
USER_AGENT = os.getenv(
    "MONITOR_USER_AGENT",
    "MonVoyageBot/0.1 (+https://example.invalid; for dev/testing)",
)

def _stable_json_hash(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _simple_diff(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight diff: reports only keys whose values changed.
    Good enough for "did something change?" + human-readable audit.
    """
    changes: Dict[str, Any] = {}
    keys = set(old.keys()) | set(new.keys())
    for k in keys:
        old_v = old.get(k)
        new_v = new.get(k)
        if old_v != new_v:
            changes[k] = {"old": old_v, "new": new_v}
    return changes

def fetch_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    return r.text

def _extract_jsonld(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Try to parse JSON-LD and return a simplified canonical dict.
    Many business pages include LocalBusiness schema with address/openingHours/etc.
    """
    result: Dict[str, Any] = {}
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not scripts:
        return result

    candidates = []
    for sc in scripts:
        txt = (sc.string or sc.get_text() or "").strip()
        if not txt:
            continue
        # Some pages embed multiple JSON objects or arrays.
        try:
            data = json.loads(txt)
            candidates.append(data)
        except Exception:
            # best-effort: strip trailing commas etc.
            cleaned = re.sub(r",\s*}", "}", txt)
            cleaned = re.sub(r",\s*]", "]", cleaned)
            try:
                data = json.loads(cleaned)
                candidates.append(data)
            except Exception:
                continue

    # Walk candidates to find something "LocalBusiness-like"
    def walk(node):
        if isinstance(node, dict):
            yield node
            for v in node.values():
                yield from walk(v)
        elif isinstance(node, list):
            for it in node:
                yield from walk(it)

    best = None
    for cand in candidates:
        for obj in walk(cand):
            t = obj.get("@type") if isinstance(obj, dict) else None
            if isinstance(t, list):
                t = ",".join(t)
            if isinstance(t, str) and any(
                x.lower() in t.lower()
                for x in ["localbusiness", "restaurant", "foodestablishment", "touristattraction"]
            ):
                best = obj
                break
        if best:
            break

    if not best:
        return result

    result["name"] = best.get("name")
    result["description"] = best.get("description")
    result["telephone"] = best.get("telephone") or best.get("phone")

    # address can be a dict with fields
    addr = best.get("address")
    if isinstance(addr, dict):
        parts = [
            addr.get("streetAddress"),
            addr.get("addressLocality"),
            addr.get("addressRegion"),
            addr.get("postalCode"),
            addr.get("addressCountry"),
        ]
        result["address"] = ", ".join([p for p in parts if p])
    elif isinstance(addr, str):
        result["address"] = addr

    # openingHours / openingHoursSpecification varies
    if "openingHours" in best:
        result["hours"] = best.get("openingHours")
    elif "openingHoursSpecification" in best:
        result["hours"] = best.get("openingHoursSpecification")

    return {k: v for k, v in result.items() if v is not None}

def _extract_by_css(soup: BeautifulSoup, css_rules: Dict[str, str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for field, selector in (css_rules or {}).items():
        try:
            el = soup.select_one(selector)
            if el:
                text = " ".join(el.get_text(" ", strip=True).split())
                if text:
                    out[field] = text
        except Exception:
            continue
    return out

def _extract_text_fallback(soup: BeautifulSoup) -> Dict[str, Any]:
    # Remove scripts/styles/nav/footer to reduce noise
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    # best-effort remove common noisy sections
    for sel in ["nav", "footer", "header"]:
        for tag in soup.select(sel):
            tag.decompose()
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    # Keep only first ~4000 chars for MVP.
    return {"text": text[:4000]}

def extract_structured(html: str, strategy: str, css_rules: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    strategy = (strategy or "jsonld").lower()

    if strategy == "jsonld":
        data = _extract_jsonld(soup)
        if data:
            return data
        # fallback if no JSON-LD
        return _extract_text_fallback(soup)

    if strategy == "css":
        data = _extract_by_css(soup, css_rules or {})
        if data:
            return data
        return _extract_text_fallback(soup)

    # default: text fallback
    return _extract_text_fallback(soup)

def normalize_record(url: str, category: Optional[str], record: Dict[str, Any]) -> Dict[str, Any]:
    # Keep it simple: trim strings and standardize keys.
    norm: Dict[str, Any] = {"source_url": url}
    if category:
        norm["category"] = category

    for k, v in record.items():
        if isinstance(v, str):
            norm[k] = v.strip()
        else:
            norm[k] = v
    return norm

def deterministic_embedding(text: str, dim: int = 384) -> list[float]:
    """
    Offline-friendly placeholder embedding (pure Python).

    Deterministic vector so you can wire Chroma end-to-end without a real model yet.
    Replace later with real embeddings and recreate the Chroma collection to match dim.
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "big", signed=False)
    rng = random.Random(seed)

    vec = [rng.gauss(0.0, 1.0) for _ in range(dim)]
    norm = math.sqrt(sum(x * x for x in vec)) + 1e-12
    return [x / norm for x in vec]

def upsert_place_and_snapshot(
    site: TrackedSite,
    html: str,
    structured: Dict[str, Any],
) -> Tuple[int, bool, str, Optional[str], Optional[Dict[str, Any]]]:
    """
    Returns: (place_id, changed, new_hash, old_hash, diff)
    """
    init_db()
    session = get_session()
    try:
        content_hash = _stable_json_hash(structured)

        place = session.query(Place).filter(Place.source_url == site.url).one_or_none()
        old_hash = place.content_hash if place else None

        changed = (old_hash != content_hash)
        diff: Optional[Dict[str, Any]] = None
        if changed and place and isinstance(place.content_json, dict):
            diff = _simple_diff(place.content_json, structured)

        if place is None:
            place = Place(
                source_url=site.url,
                name=structured.get("name") or site.name,
                category=site.category,
                address=structured.get("address"),
                phone=structured.get("telephone") or structured.get("phone"),
                hours=_stringify_hours(structured.get("hours")),
                description=structured.get("description"),
                content_json=structured,
                content_hash=content_hash,
            )
            session.add(place)
            session.flush()
        else:
            # Update canonical truth
            place.name = structured.get("name") or place.name
            place.category = site.category or place.category
            place.address = structured.get("address") or place.address
            place.phone = structured.get("telephone") or structured.get("phone") or place.phone
            place.hours = _stringify_hours(structured.get("hours")) or place.hours
            place.description = structured.get("description") or place.description
            place.content_json = structured
            place.content_hash = content_hash

        # Append snapshot (raw_html optional - you may want to store externally later)
        snap = PlaceSnapshot(
            place_id=place.id,
            content_json=structured,
            content_hash=content_hash,
            raw_html=html,
        )
        session.add(snap)

        if changed:
            ce = ChangeEvent(
                place_id=place.id,
                old_hash=old_hash,
                new_hash=content_hash,
                diff_json=diff,
            )
            session.add(ce)

        # Update site status
        site.last_hash = content_hash
        site.last_checked_at = None  # let DB default; not critical

        session.merge(site)
        session.commit()
        return place.id, changed, content_hash, old_hash, diff
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def _stringify_hours(hours_val: Any) -> Optional[str]:
    if hours_val is None:
        return None
    if isinstance(hours_val, str):
        return hours_val
    try:
        return json.dumps(hours_val, ensure_ascii=False)
    except Exception:
        return str(hours_val)
