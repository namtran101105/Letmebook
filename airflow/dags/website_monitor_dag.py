from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from airflow.decorators import dag, task
from airflow.exceptions import AirflowSkipException

from lib.db import TrackedPage, get_session, init_db
from lib.monitor import extract_structured, fetch_html, normalize_record, upsert_place_and_snapshot
from lib.chroma_index import delete_place_docs, upsert_place_docs

DEFAULT_SCHEDULE = os.getenv("MONITOR_SCHEDULE", "@daily")


@dag(
    dag_id="website_change_monitor",
    start_date=datetime(2026, 1, 1),
    schedule=DEFAULT_SCHEDULE,
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["monvoyage", "monitoring", "rag"],
)
def website_change_monitor():

    @task
    def list_sites() -> List[Dict[str, Any]]:
        """
        Option A: list enabled tracked_pages.
        """
        init_db()
        session = get_session()
        try:
            pages = (
                session.query(TrackedPage)
                .filter(TrackedPage.enabled == True)  # noqa: E712
                .all()
            )
            if not pages:
                raise AirflowSkipException(
                    "No tracked pages found in app DB table tracked_pages. "
                    "Seed places + tracked_pages and rerun."
                )

            return [
                {
                    "id": p.id,  # tracked_pages.id
                    "place_id": p.place_id,
                    "url": p.url,
                    "page_type": p.page_type,  # overview/menu/pricing/...
                    "extract_strategy": p.extract_strategy,
                    "css_rules": p.css_rules,
                }
                for p in pages
            ]
        finally:
            session.close()

    @task
    def check_one_site(page: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch -> extract -> normalize -> upsert snapshot -> if changed, update Chroma.
        """
        init_db()
        session = get_session()
        try:
            db_page = session.query(TrackedPage).filter(TrackedPage.id == page["id"]).one()
        finally:
            session.close()

        html = fetch_html(page["url"])
        extracted = extract_structured(
            html,
            page.get("extract_strategy") or "jsonld",
            page.get("css_rules"),
        )

        # Category is no longer on TrackedPage; keep it optional.
        normalized = normalize_record(page["url"], None, extracted)

        preview = {
            "name": normalized.get("name"),
            "address": normalized.get("address"),
            "telephone": normalized.get("telephone") or normalized.get("phone"),
            "hours": normalized.get("hours"),
            "description": (normalized.get("description") or "")[:300],
            "text": (normalized.get("text") or "")[:300],
        }
        print(f"[extract preview] {page['url']} -> {preview}")

        # IMPORTANT: upsert_place_and_snapshot must accept TrackedPage
        place_id, changed, new_hash, old_hash, diff = upsert_place_and_snapshot(
            db_page, html, normalized
        )

        if changed:
            delete_place_docs(place_id)

            # Fill doc from normalized (fallbacks)
            name = normalized.get("name") or "Unknown"
            category = normalized.get("category") or ""  # optional
            address = normalized.get("address", "")
            phone = normalized.get("telephone") or normalized.get("phone") or ""
            hours = normalized.get("hours", "")
            desc = normalized.get("description", "")

            doc = "\n".join(
                [
                    f"Name: {name}",
                    f"Category: {category}",
                    f"Address: {address}",
                    f"Phone: {phone}",
                    f"Hours: {hours}",
                    f"Description: {desc}",
                    f"Source: {page['url']}",
                    f"PageType: {page.get('page_type', '')}",
                ]
            ).strip()

            upsert_place_docs(
                place_id=place_id,
                source_url=page["url"],
                category=category or None,
                doc_texts=[doc],
                metadata_extra={"content_hash": new_hash, "page_type": page.get("page_type")},
            )

        return {
            "page_id": page["id"],
            "place_id": place_id,
            "changed": changed,
            "new_hash": new_hash,
            "old_hash": old_hash,
        }

    check_one_site.expand(page=list_sites())


website_change_monitor()

