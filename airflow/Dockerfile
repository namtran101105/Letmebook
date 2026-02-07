FROM apache/airflow:2.9.3-python3.11

USER root
# build deps for lxml/psycopg2 already in many images, but keep minimal
USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

