"""
# Debugging Tool (Admin use)
## Test postgresoperator
## Life span
Forever
"""
import datetime

from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator

# create_pet_table, populate_pet_table, get_all_pets, and get_birth_date are examples of tasks created by
# instantiating the Postgres Operator

with DAG(
    dag_id="test_postgresoperator",
    start_date=datetime.datetime(2020, 2, 2),
    schedule_interval="@once",
    catchup=False,
) as dag:
    # [START postgres_operator_howto_guide_create_pet_table]
    create_pet_table = PostgresOperator(
        task_id="create_pet_table",
        postgres_conn_id="postgres_github_test",
        sql="""
            CREATE TABLE IF NOT EXISTS pet (
            pet_id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            pet_type VARCHAR NOT NULL,
            birth_date DATE NOT NULL,
            OWNER VARCHAR NOT NULL);
          """,
    )
