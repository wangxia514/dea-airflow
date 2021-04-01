"""
## Utility Tool
### Index some data from S3

This is a tool to index arbitrary files from S3 split by prefix.

#### Utility customisation

The DAG can be parameterized with run time configuration.

#### example conf in json format
    {
        "products": "ga_ls_wo_3",
        "path_template": "s3://dea-public-data/derived/ga_ls_wo_3/{path:03d}/**/*.json",
        "stac": True,
        "skip_lineage": True,
        "key_name": "path",
        "key_range": (88, 117)
    }
"""

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.subdag_operator import SubDagOperator
from infra.images import INDEXER_IMAGE
from infra.variables import DB_DATABASE, DB_HOSTNAME, SECRET_AWS_NAME

DEFAULT_ARGS = {
    "owner": "Alex Leith",
    "depends_on_past": False,
    "start_date": datetime(2020, 10, 1),
    "email": ["alex.leith@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 0,
    "env_vars": {
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret(
            "env",
            "DB_DATABASE",
            SECRET_AWS_NAME,
            "database-name",
        ),
        Secret(
            "env",
            "DB_USERNAME",
            SECRET_AWS_NAME,
            "postgres-username",
        ),
        Secret(
            "env",
            "DB_PASSWORD",
            SECRET_AWS_NAME,
            "postgres-password",
        ),
    ],
}

TASK_ARGS = {
    "env_vars": DEFAULT_ARGS["env_vars"],
    "secrets": DEFAULT_ARGS["secrets"],
    "start_date": DEFAULT_ARGS["start_date"],
}


def load_subdag(parent_dag_name, child_dag_name, args, config_task_name):
    """
    Make us a subdag to hide all the sub tasks
    """
    subdag = DAG(
        dag_id=f"{parent_dag_name}.{child_dag_name}", default_args=args, catchup=False
    )

    config = "{{{{ task_instance.xcom_pull(dag_id='{}', task_ids='{}') }}}}".format(
        parent_dag_name, config_task_name
    )

    try:
        config = json.loads(config)
    except json.decoder.JSONDecodeError:
        config = {}

    product = config.get("product")
    keys = config.get("keys", [])
    key_name = config.get("key_name")
    stac = config.get("stac")
    skip_lineage = config.get("skip_lineage")
    path_template = config.get("path_template")

    with subdag:
        for key in keys:
            s3_path = path_template
            if key_name:
                s3_path = path_template.format(**{key_name: key})

            INDEXING = KubernetesPodOperator(
                namespace="processing",
                image=INDEXER_IMAGE,
                image_pull_policy="Always",
                arguments=[
                    "s3-to-dc",
                    "--no-sign-request",
                    "--stac" if stac else "",
                    "--skip-lineage" if skip_lineage else "",
                    s3_path,
                    product,
                ],
                labels={"backlog": "s3-to-dc"},
                name=f"datacube-index-{product}-{key}",
                task_id=f"{product}--Backlog-indexing-row--{key}",
                get_logs=True,
                is_delete_operator_pod=True,
                dag=subdag,
            )
    return subdag


def parse_dagrun_conf(config, **kwargs):
    product = "{{ dag_run.conf.product }}"
    path_template = "{{ dag_run.conf.path_template }}"
    stac = "{{ dag_run.conf.stac }}"
    skip_lineage = "{{ dag_run.conf.skip_lineage }}"
    key_name = "{{ dag_run.conf.key_name }}"
    key_range = "{{ dag_run.conf.key_range }}"

    if not product:
        raise Exception("Need to specify a product")

    if not path_template:
        raise Exception("Need to specify a path template")

    if not stac:
        stac = False
    else:
        stac = True

    if key_name and not key_range:
        raise Exception("If you specify a key_name you must specify a key_range")

    if key_range:
        key_range_list = list(key_range)
        keys = range(int(key_range_list[0]), int(key_range_list[1]))
    else:
        keys = ["one"]

    return {
        "product": product,
        "path_template": path_template,
        "stac": stac,
        "skip_lineage": skip_lineage,
        "key_name": key_name,
        "key_range": key_range,
    }


DAG_NAME = "utility_index_from_s3"

dag = DAG(
    dag_id=DAG_NAME,
    default_args=DEFAULT_ARGS,
    schedule_interval="@once",
    tags=["k8s", "landsat_c3", "backlog"],
    catchup=False,
)

with dag:
    TASK_NAME = f"index-from-s3"
    PARSE_TASK_NAME = f"{TASK_NAME}_PARSE_CONFIG"

    GET_CONFIG = PythonOperator(
        task_id=PARSE_TASK_NAME,
        python_callable=parse_dagrun_conf,
        op_args=["{{ dag_run.conf.products }}"],
    )

    INDEX = SubDagOperator(
        task_id=TASK_NAME,
        subdag=load_subdag(DAG_NAME, TASK_NAME, DEFAULT_ARGS, PARSE_TASK_NAME),
        default_args=DEFAULT_ARGS,
        dag=dag,
    )

    GET_CONFIG > INDEX
