"""
DEA Waterbodies processing using Conflux.

Supported configuration arguments:

shapefile
    Default "s3://dea-public-data-dev/projects/WaterBodies/c3_shp/ga_ls_wb_3_v2_dev.shp"

outdir
    Default "s3://dea-public-data-dev/projects/WaterBodies/integration_testing/timeseries_pq_v2"

product
    Default "ga_ls_wo_3".

cmd
    Datacube query to run. Default "'time in [2021-01-01, 2021-01-03]'"
    https://datacube-core.readthedocs.io/en/stable/ops/tools.html#datacube-dataset-search
    e.g. "'lat in [-36.006, -34.671]' 'lon in [142.392, 144.496]' 'gqa_mean_x in [-1, 1]'"

plugin
    Plugin to drill with. Default "waterbodies_c3".

queue_name
    Amazon SQS queue name to save processing tasks. Default "waterbodies_conflux_dev_sqs"

csvdir
    Default "s3://dea-public-data-dev/projects/WaterBodies/integration_testing/timeseries"

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

from airflow.utils.task_group import TaskGroup

from textwrap import dedent

from infra.variables import (
    DB_DATABASE,
    DB_READER_HOSTNAME,
    AWS_DEFAULT_REGION,
    DB_HOSTNAME,
    DB_PORT,
    WATERBODIES_DEV_USER_SECRET,
    SECRET_ODC_READER_NAME,
    WATERBODIES_DB_WRITER_SECRET,
)


CONFLUX_UNSTABLE_IMAGE = "geoscienceaustralia/dea-conflux:latest"
DB_TO_CSV_CONCURRENCY_NUMBER = 1000

# Default config parameters. Only grab 3 days data to test
DEFAULT_PARAMS = dict(
    shapefile="s3://dea-public-data-dev/projects/WaterBodies/c3_shp/ga_ls_wb_3_v2_dev.shp",
    outdir="s3://dea-public-data-dev/projects/WaterBodies/integration_testing/timeseries_pq_v2",
    product="ga_ls_wo_3",
    cmd="'time in [2021-01-01, 2021-01-03]'",
    plugin="waterbodies_c3",
    queue_name="waterbodies_conflux_dev_sqs",
    csvdir="s3://dea-public-data-dev/projects/WaterBodies/integration_testing/timeseries",
    flags="--overwrite",
)

# Requested memory. Memory limit is twice this.
CONFLUX_POD_MEMORY_MB = 6000

# DAG CONFIGURATION
SECRETS = {
    "env_vars": {
        "DB_HOSTNAME": DB_READER_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "DB_PORT": DB_PORT,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
        "WATERBODIES_DB_HOST": DB_HOSTNAME,
        "WATERBODIES_DB_PORT": DB_PORT,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "WATERBODIES_DB_NAME", WATERBODIES_DB_WRITER_SECRET, "database-name"),
        Secret("env", "WATERBODIES_DB_USER", WATERBODIES_DB_WRITER_SECRET, "postgres-username"),
        Secret("env", "WATERBODIES_DB_PASS", WATERBODIES_DB_WRITER_SECRET, "postgres-password"),
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
    "k8s_waterbodies_conflux_dev",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0 0 * * 1-5",  # runs at 00:00 on every day-of-week from Monday through Friday
    catchup=False,
    concurrency=128,
    tags=["k8s", "landsat", "waterbodies", "conflux", "integration test"],
)


def k8s_job_task(dag, queue_name):
    mem = CONFLUX_POD_MEMORY_MB
    req_mem = "{}Mi".format(int(mem))
    lim_mem = "{}Mi".format(int(mem) * 2)
    parallelism = 6

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
                                    echo DB host is $WATERBODIES_DB_HOST
                                    dea-conflux run-from-queue -v \
                                            --plugin examples/{{{{ dag_run.conf.get("plugin", "{plugin}") }}}}.conflux.py \
                                            --queue {queue} \
                                            --overedge \
                                            --partial \
                                            --shapefile {{{{ dag_run.conf.get("shapefile", "{shapefile}") }}}} \
                                            --output {{{{ dag_run.conf.get("outdir", "{outdir}") }}}} {{{{ dag_run.conf.get("flags", "{flags}") }}}}
                                    """.format(queue=queue_name,
                                               shapefile=DEFAULT_PARAMS['shapefile'],
                                               outdir=DEFAULT_PARAMS['outdir'],
                                               plugin=DEFAULT_PARAMS['plugin'],
                                               flags=DEFAULT_PARAMS['flags'],
                                               )),
                            ],
                            "env": [
                                {"name": "DB_HOSTNAME", "value": DB_READER_HOSTNAME},
                                {"name": "DB_DATABASE", "value": DB_DATABASE},
                                {"name": "WATERBODIES_DB_HOST", "value": SECRETS['env_vars']['WATERBODIES_DB_HOST']},
                                {"name": "WATERBODIES_DB_PORT", "value": SECRETS['env_vars']['WATERBODIES_DB_PORT']},
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
                                {
                                    "name": "WATERBODIES_DB_USER",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": WATERBODIES_DB_WRITER_SECRET,
                                            "key": "postgres-username",
                                        },
                                    },
                                },
                                {
                                    "name": "WATERBODIES_DB_PASS",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": WATERBODIES_DB_WRITER_SECRET,
                                            "key": "postgres-password",
                                        },
                                    },
                                },
                                {
                                    "name": "WATERBODIES_DB_NAME",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": WATERBODIES_DB_WRITER_SECRET,
                                            "key": "database-name",
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
        get_logs=False,
        body=yaml,
    )
    return job_task


def k8s_queue_push(dag, queue_name):
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
                queue=queue_name,
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


def k8s_getids(dag, cmd, product):
    """K8s pod operator to get IDs."""
    getids_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Writing to /airflow/xcom/return.json"
            dea-conflux get-ids {product} {cmd} --s3 > /airflow/xcom/return.json
            """.format(cmd=cmd, product=product)
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


def k8s_makequeue(dag, queue_name):
    # TODO(MatthewJA): Use the name/ID of this DAG
    # to make sure that we don't double-up if we're
    # running two DAGs simultaneously.
    makequeue_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-conflux image {image}"
            dea-conflux make {name}
            """.format(
                image=CONFLUX_UNSTABLE_IMAGE,
                name=queue_name
            )
        ),
    ]
    makequeue = KubernetesPodOperator(
        image=CONFLUX_UNSTABLE_IMAGE,
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


def k8s_delqueue(dag, queue_name):
    # TODO(MatthewJA): Use the name/ID of this DAG
    # to make sure that we don't double-up if we're
    # running two DAGs simultaneously.
    delqueue_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-conflux image {image}"
            dea-conflux delete {name}
            """.format(
                image=CONFLUX_UNSTABLE_IMAGE,
                name=queue_name,
            )
        ),
    ]
    delqueue = KubernetesPodOperator(
        image=CONFLUX_UNSTABLE_IMAGE,
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


def k8s_makecsvs(dag, index_num, split_num):
    makecsvs_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-conflux image {image}"
            dea-conflux db-to-csv --output {{{{ dag_run.conf.get("csvdir", "{csvdir}") }}}} --jobs 64 --verbose --index-num {index_num} --split-num {split_num}
            """.format(
                image=CONFLUX_UNSTABLE_IMAGE,
                csvdir=DEFAULT_PARAMS['csvdir'],
                index_num=index_num,
                split_num=split_num,
            )
        ),
    ]
    makecsvs = KubernetesPodOperator(
        image=CONFLUX_UNSTABLE_IMAGE,
        name="waterbodies-conflux-makecsvs-" + str(index_num),
        arguments=makecsvs_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "waterbodies-conflux-makecsvs"},
        get_logs=False,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "10000m",
            "request_memory": "8192Mi",
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="waterbodies-conflux-makecsvs-" + str(index_num),
    )
    return makecsvs


with dag:
    cmd = '{{{{ dag_run.conf.get("cmd", "{cmd}") }}}}'.format(
        cmd=DEFAULT_PARAMS['cmd'],
    )
    product = '{{{{ dag_run.conf.get("product", "{product}") }}}}'.format(
        product=DEFAULT_PARAMS['product'],
    )
    queue_name = '{{{{ dag_run.conf.get("queue_name", "{queue_name}") }}}}'.format(
        queue_name=DEFAULT_PARAMS['queue_name'],
    )

    getids = k8s_getids(dag, cmd, product)
    makequeue = k8s_makequeue(dag, queue_name)
    # Populate the queues.
    push = k8s_queue_push(dag, queue_name)
    # Now we'll do the main task.
    task = k8s_job_task(dag, queue_name)
    # Finally delete the queue.
    delqueue = k8s_delqueue(dag, queue_name)
    # Then update the DB -> CSV.

    with TaskGroup(group_id="makecsvs") as makecsvs:
        for index in range(DB_TO_CSV_CONCURRENCY_NUMBER):
            # only run 0.2% workload as the integration test
            if index == 0 or index == 1:
                makecsv = k8s_makecsvs(dag, index_num=index, split_num=DB_TO_CSV_CONCURRENCY_NUMBER)

    getids >> makequeue >> push >> task >> delqueue >> makecsvs
