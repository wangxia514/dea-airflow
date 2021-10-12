"""
DEA Waterbodies processing using Conflux.

Supported configuration arguments:

shapefile
    Default "s3://dea-public-data/projects/WaterBodies/DEA_Waterbodies_shapefile/AusWaterBodiesFINALStateLink.shp"

outdir
    Appended to s3://dea-public-data-dev/waterbodies/conflux/.
    Default "default-out"

cmd
    Datacube query to run. Default "--limit 1"

flags
    Other flags to pass to Conflux.

"""
from datetime import datetime, timedelta

# import json

from airflow import DAG
from airflow_kubernetes_job_operator.kubernetes_job_operator import (
    KubernetesJobOperator,
)  # noqa: E501
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from textwrap import dedent

from infra.images import CONFLUX_UNSTABLE_IMAGE, WATERBODIES_UNSTABLE_IMAGE

from infra.variables import (
    DB_DATABASE,
    DB_READER_HOSTNAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
    WATERBODIES_DEV_USER_SECRET,
    SECRET_ODC_READER_NAME,
)

# Requested memory. Memory limit is twice this.
CONFLUX_POD_MEMORY_MB = 3000

# DAG CONFIGURATION
SECRETS = {
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
    **SECRETS,
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
    {
        "key": "dedicated",
        "operator": "Equal",
        "value": "waterbodies",
        "effect": "NoSchedule",
    }
]

# THE DAG
dag = DAG(
    "k8s_waterbodies_conflux",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # triggered only
    catchup=False,
    concurrency=128,
    tags=["k8s", "landsat", "waterbodies", "conflux"],
)


def k8s_job_task(dag):
    mem = CONFLUX_POD_MEMORY_MB
    req_mem = "{}Mi".format(int(mem))
    lim_mem = "{}Mi".format(int(mem) * 2)
    parallelism = 128
    yaml = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": "waterbodies-conflux-job",
                     "namespace": "processing"},
        "spec": {
            "parallelism": parallelism,
            "backoffLimit": 3,
            "template": {
                "spec": {
                    "restartPolicy": "OnFailure",
                    "tolerations": tolerations,
                    "affinity": affinity,
                    "containers": [
                        {
                            "name": "conflux",
                            "image": CONFLUX_UNSTABLE_IMAGE,
                            "imagePullPolicy": "IfNotPresent",
                            "resources": {
                                "requests": {
                                    "cpu": "1000m",
                                    "memory": req_mem,
                                },
                                "limits": {
                                    "cpu": "1000m",
                                    "memory": lim_mem,
                                },
                            },
                            "command": ["/bin/bash"],
                            "args": [
                                "-c",
                                dedent(
                                    """
                                    echo Default region $AWS_DEFAULT_REGION
                                    hostname -I
                                    dea-conflux run-from-queue -v \
                                            --plugin examples/waterbodies.conflux.py \
                                            --queue {queue} \
                                            --overedge \
                                            --partial \
                                            --shapefile {{{{ dag_run.conf.get("shapefile", "s3://dea-public-data/projects/WaterBodies/DEA_Waterbodies_shapefile/AusWaterBodiesFINALStateLink.shp") }}}} \
                                            --output s3://dea-public-data-dev/waterbodies/conflux/{{{{ dag_run.conf.get("outdir", "default-out") }}}} {{{{ dag_run.conf.get("flags", "") }}}}
                                    """.format(queue="waterbodies_conflux_sqs")
                                ),
                            ],
                            "env": [
                                {"name": "DB_HOSTNAME", "value": DB_READER_HOSTNAME},
                                {"name": "DB_DATABASE", "value": DB_DATABASE},
                                {"name": "AWS_NO_SIGN_REQUEST", "value": "YES"},
                                {"name": "DB_PORT", "value": DB_PORT},
                                {
                                    "name": "AWS_DEFAULT_REGION",
                                    "value": AWS_DEFAULT_REGION,
                                },
                                {
                                    "name": "DB_USERNAME",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": SECRET_ODC_READER_NAME,
                                            "key": "postgres-username",
                                        },
                                    },
                                },
                                {
                                    "name": "DB_PASSWORD",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": SECRET_ODC_READER_NAME,
                                            "key": "postgres-password",
                                        },
                                    },
                                },
                                {
                                    "name": "AWS_ACCESS_KEY_ID",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": WATERBODIES_DEV_USER_SECRET,
                                            "key": "AWS_ACCESS_KEY_ID",
                                        },
                                    },
                                },
                                {
                                    "name": "AWS_SECRET_ACCESS_KEY",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": WATERBODIES_DEV_USER_SECRET,
                                            "key": "AWS_SECRET_ACCESS_KEY",
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
            },
        },
    }

    job_task = KubernetesJobOperator(
        image=CONFLUX_UNSTABLE_IMAGE,
        dag=dag,
        task_id="waterbodies-conflux-run",
        get_logs=True,
        body=yaml,
    )
    return job_task


def k8s_queue_push(dag):
    cmd = [
        "bash",
        "-c",
        dedent(
            """
            # Download the IDs file from xcom.
            echo "Downloading {{{{ ti.xcom_pull(task_ids='waterbodies-conflux-getids')['ids_path'] }}}}"
            aws s3 cp {{{{ ti.xcom_pull(task_ids='waterbodies-conflux-getids')['ids_path'] }}}} ids.txt

            # Push the IDs to the queue.
            dea-conflux push-to-queue --txt ids.txt --queue {queue}
            """.format(
                queue="waterbodies_conflux_sqs",
            )
        ),
    ]
    return KubernetesPodOperator(
        image=CONFLUX_UNSTABLE_IMAGE,
        dag=dag,
        name="waterbodies-conflux-push",
        arguments=cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "waterbodies-conflux-push"},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": "512Mi",
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="waterbodies-conflux-push",
    )


def k8s_getids(dag, cmd):
    """K8s pod operator to get IDs."""
    getids_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Writing to /airflow/xcom/return.json"
            dea-conflux get-ids wofs_albers {cmd} --s3 > /airflow/xcom/return.json
            """.format(cmd=cmd)
        ),
    ]

    getids = KubernetesPodOperator(
        image=CONFLUX_UNSTABLE_IMAGE,
        name="waterbodies-conflux-getids",
        arguments=getids_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "waterbodies-conflux-getids"},
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
        task_id="waterbodies-conflux-getids",
    )
    return getids


def k8s_makequeue(dag):
    # TODO(MatthewJA): Use the name/ID of this DAG
    # to make sure that we don't double-up if we're
    # running two DAGs simultaneously.
    queue_name = "waterbodies_conflux_sqs"
    makequeue_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-waterbodies image {image}"
            python -m dea_waterbodies.queues make {name}
            """.format(
                image=WATERBODIES_UNSTABLE_IMAGE,
                name=queue_name,
            )
        ),
    ]
    makequeue = KubernetesPodOperator(
        image=WATERBODIES_UNSTABLE_IMAGE,
        name="waterbodies-conflux-makequeue",
        arguments=makequeue_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "waterbodies-conflux-makequeue"},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": "512Mi",
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="waterbodies-conflux-makequeue",
    )
    return makequeue


def k8s_delqueue(dag):
    # TODO(MatthewJA): Use the name/ID of this DAG
    # to make sure that we don't double-up if we're
    # running two DAGs simultaneously.
    queue_name = "waterbodies_conflux_sqs"
    delqueue_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-waterbodies image {image}"
            python -m dea_waterbodies.queues delete {name}
            """.format(
                image=WATERBODIES_UNSTABLE_IMAGE,
                name=queue_name,
            )
        ),
    ]
    delqueue = KubernetesPodOperator(
        image=WATERBODIES_UNSTABLE_IMAGE,
        name="waterbodies-conflux-delqueue",
        arguments=delqueue_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "waterbodies-conflux-delqueue"},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": "512Mi",
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="waterbodies-conflux-delqueue",
    )
    return delqueue


with dag:
    cmd = '{{ dag_run.conf.get("cmd", "--limit=1") }}'

    getids = k8s_getids(dag, cmd)
    makequeue = k8s_makequeue(dag)
    # Populate the queues.
    push = k8s_queue_push(dag)
    # Now we'll do the main task.
    task = k8s_job_task(dag)
    # Finally delete the queue.
    delqueue = k8s_delqueue(dag)
    getids >> makequeue >> push >> task >> delqueue
