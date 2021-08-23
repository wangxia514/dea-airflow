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

"""

from datetime import datetime, timedelta

from airflow import DAG

from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.sql import SQLCheckOperator, BranchSQLOperator
from infra.connections import DB_ODC_READER_CONN

# from dea_utils.update_explorer_summaries import explorer_forcerefresh_operator

DAG_NAME = "testing_utility_select_dataset_in_years"

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

# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    # template_searchpath="dags/deletion/",
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "self-service", "delete-datasets", "explorer-update"],
)

with dag:

    branchop = BranchSQLOperator(
        task_id="select_dataset_in_years_branchsqloperator",
        conn_id=DB_ODC_READER_CONN,
        sql="""
        SELECT count(*)
        FROM   agdc.dataset ds
        WHERE  ds.dataset_type_ref = (SELECT id
                                    FROM   agdc.dataset_type dt
                                    WHERE  dt.NAME = '{{ dag_run.conf['product_name'] }}')
        AND ( ds.metadata -> 'extent' ->> 'center_dt' LIKE '{{ dag_run.conf['selected_year'] }}%')
        LIMIT 1;
        """,
        follow_task_ids_if_true="select_dataset_in_dt_years",
        follow_task_ids_if_false="select_dataset_in_dtr_years",
        # parameters={"product_name": "ls5_fc_albers", "selected_year": "1986"},
    )

    checkop = SQLCheckOperator(
        task_id="select_dataset_in_years_sqlcheckoperator",
        conn_id=DB_ODC_READER_CONN,
        sql="""
        SELECT count(ds.id)
        FROM   agdc.dataset ds
        WHERE  ds.dataset_type_ref = (SELECT id
                                    FROM   agdc.dataset_type dt
                                    WHERE  dt.NAME = '{{ dag_run.conf['product_name'] }}')
        """,
    )

    followA = PostgresOperator(
        task_id="select_dataset_in_dt_years",
        postgres_conn_id=DB_ODC_READER_CONN,
        sql="""
--------------------------------------
-- SQL to Delete datasets from product in year (Y1, Y2)
--------------------------------------
SET search_path = 'agdc';
-------------------------------------
-- Matching dataset location and delete
-------------------------------------
SELECT Count(*)
FROM   dataset_location dl
WHERE  dl.dataset_ref in
       (
            SELECT ds.id
            FROM   agdc.dataset ds
            WHERE  ds.dataset_type_ref = (SELECT id
                                        FROM   agdc.dataset_type dt
                                        WHERE  dt.NAME = '{{ params.product_name }}')
            AND ( ds.metadata -> 'extent' ->> 'center_dt' LIKE '{{ params.selected_year }}%')
        );
        """,
        # params={"product_name": "{% if dag_run.conf.get('product_name') %}{{ dag_run.conf['product_name'] }}{% else %} 'ls5_fc_albers' {% endif %}" },
        params={
            "product_name": "{{ dag_run.conf['product_name'] }}",
            "selected_year": "{{ dag_run.conf['selected_year'] }}",
        },
    )

    followB = PostgresOperator(
        task_id="select_dataset_in_dtr_years",
        postgres_conn_id=DB_ODC_READER_CONN,
        sql="""
--------------------------------------
-- SQL to Delete datasets from product in year (Y1, Y2)
--------------------------------------
SET search_path = 'agdc';
-------------------------------------
-- Matching dataset location and delete
-------------------------------------
SELECT Count(*)
FROM   dataset_location dl
WHERE  dl.dataset_ref in
       (
            SELECT ds.id
            FROM   dataset ds
            WHERE  ds.dataset_type_ref = (SELECT id
                                        FROM   dataset_type dt
                                        WHERE  dt.NAME = '{{ params.product_name }}')
            AND ( ds.metadata -> 'properties' ->> 'dtr:start_datetime' LIKE '{{ params.selected_year }}%')
        );
        """,
        # params={"product_name": "{% if dag_run.conf.get('product_name') %}{{ dag_run.conf['product_name'] }}{% else %} 'ls5_fc_albers' {% endif %}" },
        params={
            "product_name": "{{ dag_run.conf['product_name'] }}",
            "selected_year": "{{ dag_run.conf['selected_year'] }}",
        },
    )

    # PostgresOperator(
    #     task_id="select_dataset_in_dt_years_sql_file",
    #     postgres_conn_id=DB_ODC_READER_CONN,
    #     sql="selection_sql/selected_dt_years_dataset.sql",
    #     # params={"product_name": "{% if dag_run.conf.get('product_name') %}{{ dag_run.conf['product_name'] }}{% else %} 'ls5_fc_albers' {% endif %}" },
    #     params={"product_name": "ls5_fc_albers", "selected_year": "1986"},
    # )

    # PostgresOperator(
    #     task_id="delete_dataset",
    #     postgres_conn_id="postgres_github_test",
    #     sql="deletion_sql/delete_selected_years_dataset.sql",
    #     params={"product_name": "{{ dag_run.conf['product_name'] }}"},
    # )

    # explorer_forcerefresh_operator("{{ dag_run.conf['product_name'] }}")

    branchop >> [followA, followB]
    # checkop
