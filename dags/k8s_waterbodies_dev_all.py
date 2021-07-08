"""
DEA Waterbodies processing on dev.

DAG to run the "all" workflow of DEA Waterbodies.
"""
import configparser
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG, settings
from airflow.kubernetes.secret import Secret
from airflow.models import TaskInstance
from airflow.operators.subdag_operator import SubDagOperator
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

from textwrap import dedent

from infra.images import WATERBODIES_UNSTABLE_IMAGE

from infra.variables import (
    DB_DATABASE,
    DB_READER_HOSTNAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
    WATERBODIES_DEV_USER_SECRET,
    SECRET_ODC_READER_NAME,
)

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Matthew Alger",
    "depends_on_past": False,
    "start_date": datetime(2021, 6, 2),
    "email": ["matthew.alger@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "startup_timeout_seconds": 5 * 60,
    "env_vars": {
        "DB_HOSTNAME": DB_READER_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "DB_PORT": DB_PORT,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_ODC_READER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_READER_NAME, "postgres-password"),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            WATERBODIES_DEV_USER_SECRET,
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            WATERBODIES_DEV_USER_SECRET,
            "AWS_SECRET_ACCESS_KEY",
        ),
    ],
}

# Kubernetes autoscaling group affinity
affinity = {
    "nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [
                {
                    "matchExpressions": [
                        {
                            "key": "nodegroup",
                            "operator": "In",
                            "values": [
                                "r5-4xl-waterbodies",
                            ],
                        }
                    ]
                }
            ]
        }
    }
}

tolerations = [
    {"key": "dedicated", "operator": "Equal", "value": "waterbodies", "effect": "NoSchedule"}
]

# This is the original waterbodies command:
# parallel --delay 5 --retries 3 --load 100%  --colsep ',' python -m dea_waterbodies.make_time_series ::: $CONFIG,--part,{1..24},--chunks,$NCHUNKS

# THE DAG
dag = DAG(
    "k8s_waterbodies_dev_all",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # triggered only
    catchup=False,
    tags=["k8s", "landsat", "waterbodies"],
)

# THE SUBDAG
def distribute(parent_dag=None):
    dag = DAG(
        'k8s_waterbodies_dev_all.schedule',
        schedule_interval=None,
        default_args=DEFAULT_ARGS,
    )

    if len(parent_dag.get_active_runs()) > 0:
        xcom_result = parent_dag.get_task_instances(
            session=settings.Session,
            start_date=parent_dag.get_active_runs()[-1])[-1].xcom_pull(
                dag_id='k8s_waterbodies_dev_all.schedule',
                task_ids='waterbodies-all-getchunks')
        if xcom_result:
            print(xcom_result)
            # for i in xcom_result:
            #     test = DummyOperator(
            #         task_id=i,
            #         dag=dag
            #     )
    return dag

with dag:
    config_name = '{{ dag_run.conf.get("config_name", "config_moree_test") }}'
    config_path = f'https://raw.githubusercontent.com/GeoscienceAustralia/dea-waterbodies/stable/ts_configs/{config_name}'

    # Now we need to download the DBF and do the chunking.
    # We will do this within a Kubernetes pod.
    n_chunks = 12
    getchunks_cmd = [
        "bash",
        "-c",
        dedent("""
            echo "Using dea-waterbodies image {image}"
            python -m dea_waterbodies.make_chunks {conf} {n_chunks} > /airflow/xcom/return.json
            """.format(image=WATERBODIES_UNSTABLE_IMAGE,
                        conf=config_path,
                        n_chunks=n_chunks)
        ),
    ]
    
    getchunks = KubernetesPodOperator(
        image=WATERBODIES_UNSTABLE_IMAGE,
        name="waterbodies-all-getchunks",
        arguments=getchunks_cmd,
        image_pull_policy="IfNotPresent",
        labels={"step": "waterbodies-dev-all-getchunks"},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": "512Mi",
        },
        do_xcom_push=True,
        namespace="processing",
        tolerations=tolerations,
        task_id="waterbodies-all-getchunks",
    )

    # Now the chunking should be sent via xcom. Fire up the subdag to do scheduling.
    subdag = SubDagOperator(
        subdag=distribute(parent_dag=dag),
        task_id='schedule',
        dag=dag,
    )

    getchunks >> subdag

    # for part in range(1, n_chunks + 1):
    #     # https://airflow.apache.org/docs/apache-airflow/1.10.12/_api/airflow/contrib/operators/
    #     # kubernetes_pod_operator/index.html#airflow.providers.cncf.kubernetes.operators.kubernetes_pod.KubernetesPodOperator
    #     chunk = area_chunks[part - 1]
    #     mem = est_max_mem[part - 1]
    #     cmd = [
    #         "bash",
    #         "-c",
    #         dedent(
    #             """
    #             echo "Using dea-waterbodies image {image}"
    #             wget {conf} -O config.ini
    #             cat config.ini
    #             cat << EOF > ids.txt
    #             {{ids}}
    #             EOF
    #             cat ids.txt | python -m dea_waterbodies.make_time_series config.ini
    #             """.format(image=WATERBODIES_UNSTABLE_IMAGE,
    #                        conf=config_path)
    #         ).format(ids='\n'.join(chunk)),  # Do this here to avoid indent/dedent issues
    #     ]
    #     req_mem = "{}Mi".format(int(mem) + 128)
    #     print(f'Requesting {req_mem} for chunk {part}')
    #     KubernetesPodOperator(
    #         image=WATERBODIES_UNSTABLE_IMAGE,
    #         name="waterbodies-all",
    #         arguments=cmd,
    #         image_pull_policy="IfNotPresent",
    #         labels={"step": "waterbodies-dev-all-{part}".format(part=part)},
    #         get_logs=True,
    #         affinity=affinity,
    #         is_delete_operator_pod=True,
    #         resources={
    #             "request_cpu": "1000m",
    #             "request_memory": req_mem,
    #         },
    #         namespace="processing",
    #         tolerations=tolerations,
    #         task_id="waterbodies-all-task-{part}".format(part=part),
    #     )
