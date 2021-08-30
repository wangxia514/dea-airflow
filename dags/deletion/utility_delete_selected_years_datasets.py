"""
# Delete selected years of datasets (Self Serve)

This DAG should be triggered manually and will:

- delete selected years of datasets

## Note
All list of utility dags here: https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/deletion, see Readme

## Customisation

There are three configuration arguments:

- `product_name`

The commands which are executed are:

1. deletion sql
3. update explorer


### Sample Configuration

    {
        "product_name": "ls5_fc_albers",
        "selected_year": "1986"
    }

    {
        "product_name": "ga_ls_wo_3",
        "selected_year": "1986"
    }

## for testing

scenario 1: 4 datasets in total, type `center_dt`

    {
        "product_name": "s2a_nrt_granule",
        "selected_year": "2021"
    }

scenario 2: 1 datasets in total, type `dtr:start_datetime`

    {
        "product_name": "ga_ls8c_ard_provisional_3",
        "selected_year": "2021"
    }

"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.hooks.postgres_hook import PostgresHook

from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python_operator import PythonOperator

from infra.connections import DB_ODC_READER_CONN
from deletion.deletion_sql_queries import (
    DATASET_COUNT_CONFIRMATION,
)

# from dea_utils.update_explorer_summaries import explorer_forcerefresh_operator
from airflow.exceptions import AirflowException


DAG_NAME = "deletion_utility_select_dataset_in_years"

DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        # TODO: Pass these via templated params in DAG Run
        # "DB_HOSTNAME": DB_HOSTNAME,
        # "DB_DATABASE": DB_DATABASE,
        # "DB_PORT": DB_PORT,
        # "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
}


def datetime_metadata_selector(product_name="", selected_year="", **kwargs):
    """
    return sql query result
    """
    query_string = DATASET_COUNT_CONFIRMATION.format(product_name=product_name, selected_year=selected_year)
    print(query_string)
    pg_hook = PostgresHook(postgres_conn_id=DB_ODC_READER_CONN)
    connection = pg_hook.get_conn()
    cursor = connection.cursor()
    cursor.execute(query_string)
    result = cursor.fetchone()
    if not result or result[0] == 0:
        raise AirflowException("This product does not have any datasets for the selected year, ending the run")  # mark it failed
    else:
        print(f"{result[0]} datasets for year {selected_year} for product {product_name} can be deleted")
    return True


def deletion_confirmation(product_name="", selected_year="", **kwargs):
    """
    Query the database for the product and selected year, if datasets are found
    mark failed
    if no datasets are found, return success
    """
    query_string = DATASET_COUNT_CONFIRMATION.format(
        product_name=product_name, selected_year=selected_year
    )
    print(query_string)
    pg_hook = PostgresHook(postgres_conn_id=DB_ODC_READER_CONN)
    connection = pg_hook.get_conn()
    cursor = connection.cursor()
    cursor.execute(query_string)
    result = cursor.fetchone()
    if result[0] > 0:
        raise AirflowException(f"{result[0]} datasets remaining for the year {selected_year}, deletion failed")  # mark it failed
    else:
        print("No dataset found, deletion has successfully completed")
        return True


# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "self-service", "delete-datasets", "explorer-update"],
)

with dag:

    branchop = PythonOperator(
        task_id="select_dataset_datetime_metadata",
        python_callable=datetime_metadata_selector,
        op_kwargs={
            "product_name": "{{ dag_run.conf.product_name }}",
            "selected_year": "{{ dag_run.conf.selected_year }}",
        },
    )

    delete_selected_year_for_product = PostgresOperator(
        task_id="delete_selected_year_for_product",
        sql="deletion_sql/delete_selected_years_dataset.sql",
        postgres_conn_id=DB_ODC_READER_CONN,
        params={
            "product_name": "{{ dag_run.conf.product_name }}",
            "selected_year": "{{ dag_run.conf.selected_year }}",
        },
    )

    execution_status_reporter = PythonOperator(
        task_id="deletion_confirmation",
        python_callable=deletion_confirmation,
        op_kwargs={
            "product_name": "{{ dag_run.conf.product_name }}",
            "selected_year": "{{ dag_run.conf.selected_year }}",
        },
    )

    branchop >> delete_selected_year_for_product >> execution_status_reporter
