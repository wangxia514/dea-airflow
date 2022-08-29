# -*- coding: utf-8 -*-

"""
marine ungrouped user stats dag
"""
# pylint: disable=C0301
# pylint: disable=W0104
# pylint: disable=E0401
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy import DummyOperator
from airflow.models import Variable

from infra.variables import REPORTING_IAM_REP_S3_SECRET
from automated_reporting import k8s_secrets, utilities

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": datetime(2021, 9, 1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 90,
    "retry_delay": timedelta(days=1),
    "secrets": [
        Secret("env", "ACCESS_KEY", REPORTING_IAM_REP_S3_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", REPORTING_IAM_REP_S3_SECRET, "SECRET_KEY"),
    ],
}
ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.4.4"
)
dag = DAG(
    "rep_marine_monthly_prod",
    description="DAG for marine ungrouped user stats",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 1 * *",
)


with dag:
    # JOBS1 = [
    #    "echo fk1 user stats ingestion: $(date)",
    #    "pip install ga-reporting-etls==1.18.0",
    #    "jsonresult=`python3 -c 'from nemo_reporting.user_stats import fk1_user_stats_ingestion; fk1_user_stats_ingestion.task()'`",
    #    "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    # ]
    # JOBS2 = [
    #    "echo fk1 user stats processing: $(date)",
    #    "pip install ga-reporting-etls==1.18.0",
    #    "jsonresult=`python3 -c 'from nemo_reporting.user_stats import fk1_user_stats_processing; fk1_user_stats_processing.task()'`",
    # ]
    # JOBS3 = [
    #    "echo iy57 user stats ingestion: $(date)",
    #    "pip install ga-reporting-etls==1.18.0",
    #    "jsonresult=`python3 -c 'from nemo_reporting.user_stats import iy57_user_stats_ingestion; iy57_user_stats_ingestion.task()'`",
    #    "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    # ]
    # JOBS4 = [
    #    "echo iy57 user stats processing: $(date)",
    #    "pip install ga-reporting-etls==1.18.0",
    #    "jsonresult=`python3 -c 'from nemo_reporting.user_stats import iy57_user_stats_processing; iy57_user_stats_processing.task()'`",
    # ]
    # JOBS5 = [
    #    "echo pw31 user stats ingestion: $(date)",
    #    "pip install ga-reporting-etls==1.18.0",
    #    "jsonresult=`python3 -c 'from nemo_reporting.user_stats import pw31_user_stats_ingestion; pw31_user_stats_ingestion.task()'`",
    #    "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    # ]
    # JOBS6 = [
    #    "echo pw31 user stats processing: $(date)",
    #    "pip install ga-reporting-etls==1.18.0",
    #    "jsonresult=`python3 -c 'from nemo_reporting.user_stats import pw31_user_stats_processing; pw31_user_stats_processing.task()'`",
    # ]
    JOBS7 = [
        "echo Elvis ingestion processing: $(date)",
        "parse-uri $REP_DB_URI /tmp/env; source /tmp/env",
        "marine-elvis-ingestion",
    ]
    START = DummyOperator(task_id="marine-monthly-stats")
    # fk1_ingestion = KubernetesPodOperator(
    #    namespace="processing",
    #    image="python:3.8-slim-buster",
    #    arguments=["bash", "-c", " &&\n".join(JOBS1)],
    #    name="write-xcom",
    #    do_xcom_push=True,
    #    is_delete_operator_pod=True,
    #    in_cluster=True,
    #    task_id="fk1_ingestion",
    #    get_logs=True,
    #    env_vars={
    #        "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
    #        "FILE_TO_PROCESS": "fk1",
    #    },
    # )
    # fk1_processing = KubernetesPodOperator(
    #    namespace="processing",
    #    image="python:3.8-slim-buster",
    #    arguments=["bash", "-c", " &&\n".join(JOBS2)],
    #    name="fk1_processing",
    #    do_xcom_push=False,
    #    is_delete_operator_pod=True,
    #    in_cluster=True,
    #    task_id="fk1_processing",
    #    get_logs=True,
    #    env_vars={
    #        "AGGREGATION_MONTHS": "{{ task_instance.xcom_pull(task_ids='fk1_ingestion') }}",
    #        "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
    #    },
    # )
    # iy57_ingestion = KubernetesPodOperator(
    #    namespace="processing",
    #    image="python:3.8-slim-buster",
    #    arguments=["bash", "-c", " &&\n".join(JOBS3)],
    #    name="write-xcom",
    #    do_xcom_push=True,
    #    is_delete_operator_pod=True,
    #    in_cluster=True,
    #    task_id="iy57_ingestion",
    #    get_logs=True,
    #    env_vars={
    #        "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
    #        "FILE_TO_PROCESS": "iy57",
    #    },
    # )
    # iy57_processing = KubernetesPodOperator(
    #    namespace="processing",
    #    image="python:3.8-slim-buster",
    #    arguments=["bash", "-c", " &&\n".join(JOBS4)],
    #    name="iy57_processing",
    #    do_xcom_push=False,
    #    is_delete_operator_pod=True,
    #    in_cluster=True,
    #    task_id="iy57_processing",
    #    get_logs=True,
    #    env_vars={
    #        "AGGREGATION_MONTHS": "{{ task_instance.xcom_pull(task_ids='iy57_ingestion') }}",
    #        "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
    #    },
    # )
    # pw31_ingestion = KubernetesPodOperator(
    #    namespace="processing",
    #    image="python:3.8-slim-buster",
    #    arguments=["bash", "-c", " &&\n".join(JOBS5)],
    #    name="write-xcom",
    #    do_xcom_push=True,
    #    is_delete_operator_pod=True,
    #    in_cluster=True,
    #    task_id="pw31_ingestion",
    #    get_logs=True,
    #    env_vars={
    #        "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
    #        "FILE_TO_PROCESS": "pw31",
    #    },
    # )
    # pw31_processing = KubernetesPodOperator(
    #    namespace="processing",
    #    image="python:3.8-slim-buster",
    #    arguments=["bash", "-c", " &&\n".join(JOBS6)],
    #    name="pw31_processing",
    #    do_xcom_push=False,
    #    is_delete_operator_pod=True,
    #    in_cluster=True,
    #    task_id="pw31_processing",
    #    get_logs=True,
    #    env_vars={
    #        "AGGREGATION_MONTHS": "{{ task_instance.xcom_pull(task_ids='pw31_ingestion') }}",
    #        "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
    #    },
    # )
    elvis_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Elvis ingestion processing: $(date)",
            "parse-uri $REP_DB_URI /tmp/env; source /tmp/env",
            "marine-elvis-ingestion",
        ],
        task_id="elvis_ingestion",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "REPORTING_BUCKET": Variable.get("reporting_s3_bucket"),
        },
        secrets=k8s_secrets.db_secrets(ENV),
    )
    # START >> fk1_ingestion >> fk1_processing
    # START >> iy57_ingestion >> iy57_processing
    # START >> pw31_ingestion >> pw31_processing
    START >> elvis_ingestion
