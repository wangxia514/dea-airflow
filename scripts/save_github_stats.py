"""
Export GitHub Stats from ElasticSearch and save to PostgreSQL
"""

import logging
import os

import boto3
import psycopg2
from psycopg2.extras import Json

import elasticsearch_dsl
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch_dsl import Search
from requests_aws4auth import AWS4Auth
from tqdm import tqdm

LOG = logging.getLogger()

ES_HOST = "search-digitalearthaustralia-lz7w5p3eakto7wrzkmg677yebm.ap-southeast-2.es.amazonaws.com"
ES_PORT = int(os.environ.get("ES_PORT", 443))
AWS_REGION = "ap-southeast-2"


def ensure_pg_table(conn):
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS gh_metrics_raw (
    timestamp timestamp,
    repo text,
    data jsonb,
    PRIMARY KEY (timestamp, repo));"""
    )
    cur.close()


def save_record_to_pg(conn, record):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO gh_metrics_raw (timestamp, repo, data) VALUES(%s, %s, %s)
        ON CONFLICT DO NOTHING
    """,
        [record["@timestamp"], record["nameWithOwner"], Json(record)],
    )
    cur.close()


def main():
    pg_conn = get_pg_connection()
    ensure_pg_table(pg_conn)

    es_client = get_es_connection()
    s = Search(using=es_client, index="github-stats-*")

    print(f"{s.count()} matching results.")
    response = s.execute()

    records = response.hits.total
    # print(response.hits.total)
    # for hit in tqdm(response):
    for hit in tqdm(s.scan(), total=records, unit="record"):
        # print(hit.to_dict())
        save_record_to_pg(pg_conn, hit.to_dict())

    pg_conn.commit()


def get_pg_connection():
    conn = psycopg2.connect("host=localhost user=omad")
    return conn


def get_es_connection():
    LOG.info("Connecting to the ElasticSearch Endpoint, {%s}:{%s}", ES_HOST, ES_PORT)
    credentials = boto3.Session().get_credentials()
    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        AWS_REGION,
        "es",
        session_token=credentials.token,
    )

    conn = Elasticsearch(
        hosts=[{"host": ES_HOST, "port": ES_PORT}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )
    return conn


if __name__ == "__main__":
    main()
