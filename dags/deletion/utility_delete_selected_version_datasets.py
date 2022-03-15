"""
# Delete selected version of datasets (Self Serve)

This DAG should be triggered manually and will:

- delete selected datasets matching condition: product_name='something', version='2.5.0', sensor='landsat-8'

## Note
All list of utility dags here: https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/deletion, see Readme

## Customisation

There are three configuration arguments:

- `product_name`
- `version`
- `sensor`

The tasks steps in this dag which are executed are:

1. pre-check there is dataset for deletion for the given product with the condition, if no dataset found this dag will fail
2. execute the deletion
3. confirm deletion successed, if dataset are still found, this dag will fail


### Sample Configuration
    {
        "product_name": "ga_ls_fc_3",
        "version": "2.5.0"
        "sensor": "landsat-8"
    }

## for local integration testing testing

```
    docker-compose -f docker-compose.workflow.yaml run airflow-worker \
        airflow dags trigger --conf '{"product_name": "ga_ls7e_ard_provisional_3", "version": "3.2.0", "sensor": "landsat-7"}' deletion_utility_datasets_version_sensor

```
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.hooks.postgres_hook import PostgresHook

from airflow.operators.python_operator import PythonOperator

from infra.connections import DB_ODC_READER_CONN, DB_ODC_WRITER_CONN
from airflow.exceptions import AirflowException
from deletion.deletion_sql_queries import (
    DATASET_COUNT_BY_ANY_CLAUSE,
)


DAG_NAME = "deletion_utility_datasets_version_sensor"

DEFAULT_ARGS = {
    "owner": "Emma Ai",
    "depends_on_past": False,
    "start_date": datetime(2022, 3, 10),
    "email": ["emma.ai@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

version = "{{ dag_run.conf.version }}"
sensor = "{{ dag_run.conf.sensor }}"

SQL_WHERE_CLAUSE = """
    (ds.metadata -> 'properties' ->> 'odc:dataset_version' = '%s')
    and (ds.metadata -> 'properties' ->> 'eo:platform' = '%s')
    """ % (
    version,
    sensor,
)


def count_datasets(product_name="", where_clause="", after_delete=False, **kwargs):
    """
    Check if datasets exist, and
    Count no. datasets
    after_delete: True/False indicates the results after/before deletion
    """
    query_string = DATASET_COUNT_BY_ANY_CLAUSE.format(
        product_name=product_name, clause=where_clause
    )

    print(query_string)
    pg_hook = PostgresHook(postgres_conn_id=DB_ODC_READER_CONN)
    connection = pg_hook.get_conn()
    cursor = connection.cursor()
    cursor.execute(query_string)
    result = cursor.fetchone()
    if not result or result[0] == 0:
        if not after_delete:
            raise AirflowException(
                "No dataset in %s satisfies %s" % (product_name, where_clause)
            )  # mark it failed
        else:
            print("No dataset found, deletion has successfully completed")
            return True

    else:
        if not after_delete:
            print(
                f"{result[0]} datasets of product {product_name} with {where_clause} can be deleted"
            )
            return True
        else:
            raise AirflowException(
                f"{result[0]} datasets of product {product_name} with {where_clause} remaining, deletion failed"
            )


def delete_selected_datasets(product_name="", where_clause="", **kwargs):
    """
    Delete the datasets of product_name by where_clause
    """
    pg_hook = PostgresHook(postgres_conn_id=DB_ODC_WRITER_CONN)
    sql = kwargs["templates_dict"]["sql"]
    query_string = sql.format(product_name=product_name, clause=where_clause)
    pg_hook.run(query_string)


# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=[
        "k8s",
        "self-service",
        "datasets-deletion",
        "deletion",
    ],
)

with dag:

    branchop = PythonOperator(
        task_id="count_datasets_before_delete",
        python_callable=count_datasets,
        op_kwargs={
            "product_name": "{{ dag_run.conf.product_name }}",
            "where_clause": SQL_WHERE_CLAUSE,
            "after_delete": False,
        },
    )

    delete_selected_datasets = PythonOperator(
        task_id="delete_selected_datasets",
        python_callable=delete_selected_datasets,
        op_kwargs={
            "product_name": "{{ dag_run.conf.product_name }}",
            "where_clause": SQL_WHERE_CLAUSE,
        },
        templates_dict={"sql": "deletion_sql/delete_datasets_wild_card.sql"},
        templates_exts=(".sql",),
    )

    execution_status_reporter = PythonOperator(
        task_id="count_datasets_after_delete",
        python_callable=count_datasets,
        op_kwargs={
            "product_name": "{{ dag_run.conf.product_name }}",
            "where_clause": SQL_WHERE_CLAUSE,
            "after_delete": True,
        },
    )

    branchop >> delete_selected_datasets >> execution_status_reporter
