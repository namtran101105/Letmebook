# MonVoyage Dev — Airflow + AppDB (Postgres) + Chroma

This repository runs a local **website monitoring + RAG pipeline** using Docker. The system consists of three main components: **Postgres (App DB)** for storing places, tracked pages, snapshots, and detected changes; **Apache Airflow** for orchestrating a DAG called `website_change_monitor` that periodically fetches websites, extracts and normalizes content, stores snapshots and hashes, detects changes, and triggers re-indexing; and **Chroma** for storing vector documents used for retrieval (RAG). The high-level flow is: website → Airflow DAG → Postgres (snapshots + change events) → Chroma (only updated when content changes).

## Prerequisites
You need Docker Desktop installed and running, `docker compose` available, and you must be in the repository root where `docker-compose.dev.yml` exists. Optional but helpful tools include `curl` and `psql`, though all required actions can be performed inside containers.

## Getting Started
1. Build Docker and start all services, run:
  ```bash
  docker compose -f docker-compose.dev.yml up -d --build
  ```
2. Then verify containers are running:
   ```bash
   docker compose -f docker-compose.dev.yml ps
   ```
3. From here, you should see containers such as airflow-webserver, airflow-scheduler, airflow-postgres, appdb, and chroma.

## Create Airflow Admin User and turn on database
- Airflow does not create users automatically. Create an admin user with:
  ```bash
  docker compose -f docker-compose.dev.yml exec airflow-webserver bash -lc '
  airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
  '
  ```
- Run seeds:
  ```bash
  docker compose -f docker-compose.dev.yml exec airflow-webserver bash -lc \
  "python /opt/airflow/dags/lib/seed_tracked_sites.py"
  ```

## Launch the Airflow UI
- The UI is live at http://localhost:8080/home

## Verifying Data Changes
1. Display database table:
```bash
  docker compose -f docker-compose.dev.yml exec appdb psql -U app -d app
  \dt
```
2. Some commands to keep track of changes
```bash
  SELECT id, place_id, url, page_type, extract_strategy, enabled
  FROM tracked_pages;
```

```bash
  SELECT id, place_key, canonical_name, category
  FROM places;
```

```bash
  SELECT id, tracked_page_id, content_hash, checked_at
  FROM page_snapshots
  ORDER BY checked_at DESC
  LIMIT 5;
```