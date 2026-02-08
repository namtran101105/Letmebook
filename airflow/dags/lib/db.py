# lib/db.py
from __future__ import annotations

import os
from sqlalchemy import (
    JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, Index, create_engine, func
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

def get_app_db_url() -> str:
    return os.getenv("APP_DB_URL", "postgresql+psycopg2://app:app@appdb:5432/app")

_engine = None
_SessionLocal = None

def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(get_app_db_url(), pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine

def get_session():
    if _SessionLocal is None:
        get_engine()
    return _SessionLocal()

def init_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True)

    # existing fields
    place_key = Column(String(128), nullable=False, unique=True)
    canonical_name = Column(String(256), nullable=True)
    city = Column(String(128), nullable=True)
    category = Column(String(64), nullable=True)
    profile_json = Column(JSON, nullable=False, default=dict)
    profile_hash = Column(String(128), nullable=True)

    # ✅ add fields expected by current DAG/monitor
    source_url = Column(Text, nullable=True, unique=True)   # monitor uses this to look up Place
    name = Column(String(256), nullable=True)
    address = Column(String(512), nullable=True)
    phone = Column(String(128), nullable=True)
    hours = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    content_json = Column(JSON, nullable=False, default=dict)
    content_hash = Column(String(128), nullable=True)

    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    pages = relationship("TrackedPage", back_populates="place", cascade="all, delete-orphan")



class TrackedPage(Base):
    __tablename__ = "tracked_pages"

    id = Column(Integer, primary_key=True)
    place_id = Column(Integer, ForeignKey("places.id"), nullable=False)

    url = Column(Text, nullable=False)
    page_type = Column(String(64), nullable=False, default="overview")  # overview/menu/pricing/etc.
    extract_strategy = Column(String(32), nullable=False, default="jsonld")  # jsonld|css|text
    css_rules = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)

    last_hash = Column(String(128), nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)

    place = relationship("Place", back_populates="pages")

    __table_args__ = (
        UniqueConstraint("url", name="uq_tracked_pages_url"),
        Index("ix_tracked_pages_place_id", "place_id"),
    )


class PageSnapshot(Base):
    __tablename__ = "page_snapshots"

    id = Column(Integer, primary_key=True)
    tracked_page_id = Column(Integer, ForeignKey("tracked_pages.id"), nullable=False)

    checked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    content_json = Column(JSON, nullable=False)
    content_hash = Column(String(128), nullable=False)
    raw_html = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_page_snapshots_tracked_page_id", "tracked_page_id"),
    )


class PlaceFact(Base):
    """
    Structured facts extracted from any tracked page.
    Examples:
      - fact_type='hours' payload={'hours': '...'}
      - fact_type='menu' payload={'sections': [...], 'text': '...'}
      - fact_type='price' payload={'range': '$$', 'items': [...]}
      - fact_type='tags' payload={'tags': ['family-friendly', ...]}
    """
    __tablename__ = "place_facts"

    id = Column(Integer, primary_key=True)
    place_id = Column(Integer, ForeignKey("places.id"), nullable=False)
    source_url = Column(Text, nullable=False)
    page_type = Column(String(64), nullable=True)

    fact_type = Column(String(64), nullable=False)
    payload_json = Column(JSON, nullable=False, default=dict)

    extracted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    content_hash = Column(String(128), nullable=True)

    __table_args__ = (
        Index("ix_place_facts_place_id", "place_id"),
        Index("ix_place_facts_fact_type", "fact_type"),
    )

# --- Compatibility layer for the current DAG/monitor imports ---
# Your code expects:
#   TrackedSite        -> we map to tracked_pages
#   PlaceSnapshot      -> we map to page_snapshots
#   ChangeEvent        -> (not currently in your schema) add a small table
# and it expects Place to have:
#   source_url, name, address, phone, hours, description, content_json, content_hash

class TrackedSite(TrackedPage):
    """
    Backwards-compatible alias:
    current DAG expects 'TrackedSite' but your schema uses 'TrackedPage'.
    """
    __tablename__ = "tracked_pages"
    __mapper_args__ = {"polymorphic_identity": "tracked_site", "concrete": False}


class PlaceSnapshot(PageSnapshot):
    """
    Backwards-compatible alias:
    current monitor expects 'PlaceSnapshot' but your schema uses 'PageSnapshot'.
    """
    __tablename__ = "page_snapshots"
    __mapper_args__ = {"polymorphic_identity": "place_snapshot", "concrete": False}


class ChangeEvent(Base):
    """
    Your current schema doesn't have a change_events table.
    Add it so monitor.py can write diffs when something changes.
    """
    __tablename__ = "change_events"

    id = Column(Integer, primary_key=True)
    place_id = Column(Integer, ForeignKey("places.id"), nullable=False)
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    old_hash = Column(String(128), nullable=True)
    new_hash = Column(String(128), nullable=False)
    diff_json = Column(JSON, nullable=True)

    __table_args__ = (Index("ix_change_events_place_id", "place_id"),)

