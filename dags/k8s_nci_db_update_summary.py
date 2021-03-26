# -*- coding: utf-8 -*-

"""
### DEA NCI dev database - summarize datacube

DAG to periodically/weekly to run summarize datacube
running [Explorer](https://github.com/opendatacube/datacube-explorer)
and [Resto](https://github.com/jjrom/resto).

"""

import pendulum
from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from infra.images import EXPLORER_UNSTABLE_IMAGE, EXPLORER_IMAGE

local_tz = pendulum.timezone("Australia/Canberra")

# Templated DAG arguments
DB_HOSTNAME = "db-writer"

DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "depends_on_past": False,
    "start_date": datetime(2020, 10, 3, tzinfo=local_tz),
    "email": ["nikita.gandhi@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_PORT": "5432",
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube database connectivity
    # Use this db-users to run cubedash update-summary
    "secrets": [
        Secret("env", "DB_DATABASE", "explorer-nci-writer", "database-name"),
        Secret("env", "DB_USERNAME", "explorer-nci-writer", "postgres-username"),
        Secret("env", "DB_PASSWORD", "explorer-nci-writer", "postgres-password"),
    ],
}

dag = DAG(
    "k8s_nci_db_update_summary",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s"],
    schedule_interval="45 1 * * *",    # every day 1:45AM
)

affinity = {
    "nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [{
                "matchExpressions": [{
                    "key": "nodetype",
                    "operator": "In",
                    "values": [
                        "ondemand",
                    ]
                }]
            }]
        }
    }
}

with dag:
    START = DummyOperator(task_id="nci-db-update-summary")

    # Run update summary
    UPDATE_SUMMARY = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        # Run `cubedash-gen --help` for explanations of each option+usage
        cmds=["cubedash-gen"],
        arguments=["--no-init-database", "--refresh-stats", "--reset-incremental-position", "--all"],
        labels={"step": "summarize-datacube"},
        name="summarize-datacube",
        task_id="summarize-datacube",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
        # execution_timeout=timedelta(days=1),
    )

    # Task complete
    COMPLETE = DummyOperator(task_id="done")


    START >> UPDATE_SUMMARY
    UPDATE_SUMMARY >> COMPLETE
