"""
DEA WIT tooling processing using Conflux.

Supported configuration arguments:

shapefile
    Default "s3://dea-public-data-dev/projects/WIT/test_shp/C2_v4_NSW_only.shp"

intermediatedir
    Default "s3://dea-public-data-dev/projects/WIT/C2_v4_NSW_only_pq"

cmd
    Datacube query to run. Default "'time > 2021-01-01'"

csvdir
    Default "s3://dea-public-data-dev/projects/WIT/C2_v4_NSW_only_csv"

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

from infra.images import CONFLUX_WIT_IMAGE

from infra.variables import (
    DB_DATABASE,
    DB_READER_HOSTNAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
    WATERBODIES_DEV_USER_SECRET,
    SECRET_ODC_READER_NAME,
)

# Default config parameters.
DEFAULT_PARAMS = dict(
    shapefile="s3://dea-public-data-dev/projects/WIT/test_shp/C2_v4_NSW_only.shp",
    intermediatedir="s3://dea-public-data-dev/projects/WIT/C2_v4_NSW_only_pq",
    cmd="'time in [2021-01-01, 2099-01-01]'",
    csvdir="s3://dea-public-data-dev/projects/WIT/C2_v4_NSW_only_csv",
)

# Requested memory. Memory limit is twice this.
CONFLUX_POD_MEMORY_MB = 6000

# DAG CONFIGURATION
SECRETS = {
    "env_vars": {
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
    # Lift secrets into environment variables
    "secrets": [
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
    "owner": "Sai Ma",
    "depends_on_past": False,
    "start_date": datetime(2021, 6, 2),
    "email": ["sai.ma@ga.gov.au"],
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
        "value": "wit",
        "effect": "NoSchedule",
    }
]

# THE DAG
dag = DAG(
    "k8s_wit_conflux",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # triggered only
    catchup=False,
    concurrency=128,
    tags=["k8s", "landsat", "wit", "conflux"],
)

WIT_INPUTS = [{"product": "ga_ls5t_ard_3", "plugin": "wit_ls5", "queue": "waterbodies_conflux_sai_test_ls5_sqs"},
              {"product": "ga_ls7e_ard_3", "plugin": "wit_ls7", "queue": "waterbodies_conflux_sai_test_ls7_sqs"},
              {"product": "ga_ls8c_ard_3", "plugin": "wit_ls8", "queue": "waterbodies_conflux_sai_test_ls8_sqs"}]


def k8s_job_task(dag, queue_name, plugin):
    mem = CONFLUX_POD_MEMORY_MB
    req_mem = "{}Mi".format(int(mem))
    lim_mem = "{}Mi".format(int(mem) * 2)
    parallelism = 4

    yaml = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": "wit-conflux-job",
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
                            "image": CONFLUX_WIT_IMAGE,
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
                                    dea-conflux run-from-queue -v \
                                            --plugin examples/{plugin}.conflux.py \
                                            --queue {queue} \
                                            --overedge \
                                            --partial \
                                            --shapefile {{{{ dag_run.conf.get("shapefile", "{shapefile}") }}}} \
                                            --output {{{{ dag_run.conf.get("intermediatedir", "{intermediatedir}") }}}} {{{{ dag_run.conf.get("flags", "") }}}}
                                    """.format(queue=queue_name,
                                               shapefile=DEFAULT_PARAMS['shapefile'],
                                               intermediatedir=DEFAULT_PARAMS['intermediatedir'],
                                               plugin=plugin,
                                               )),
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
        image=CONFLUX_WIT_IMAGE,
        dag=dag,
        task_id="wit-conflux-run",
        get_logs=False,
        body=yaml,
    )
    return job_task


def k8s_queue_push(dag, queue_name, filename):
    cmd = [
        "bash",
        "-c",
        dedent(
            """
            # Download the IDs file from xcom.
            echo "Downloading {{{{ ti.xcom_pull(task_ids='wit-conflux-getids')['ids_path'] }}}}"
            aws s3 cp {{{{ ti.xcom_pull(task_ids='wit-conflux-getids')['ids_path'] }}}} {filename}

            # Push the IDs to the queue.
            dea-conflux push-to-queue --txt ids.txt --queue {queue}
            """.format(
                queue=queue_name,
                filename=filename,
            )
        ),
    ]
    return KubernetesPodOperator(
        image=CONFLUX_WIT_IMAGE,
        dag=dag,
        name="wit-conflux-push",
        arguments=cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "wit-conflux-push"},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": "512Mi",
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="wit-conflux-push",
    )


def k8s_getids(dag, cmd, product):
    """K8s pod operator to get IDs."""
    getids_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Writing to /airflow/xcom/{product}.json"
            dea-conflux get-ids {product} {cmd} --s3 > /airflow/xcom/{product}.json
            """.format(cmd=cmd, product=product)
        ),
    ]

    getids = KubernetesPodOperator(
        image=CONFLUX_WIT_IMAGE,
        name="wit-conflux-getids",
        arguments=getids_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "wit-conflux-getids"},
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
        task_id="wit-conflux-getids",
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
                image=CONFLUX_WIT_IMAGE,
                name=queue_name
            )
        ),
    ]
    makequeue = KubernetesPodOperator(
        image=CONFLUX_WIT_IMAGE,
        name="wit-conflux-makequeue",
        arguments=makequeue_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "wit-conflux-makequeue"},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": "512Mi",
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="wit-conflux-makequeue",
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
                image=CONFLUX_WIT_IMAGE,
                name=queue_name,
            )
        ),
    ]
    delqueue = KubernetesPodOperator(
        image=CONFLUX_WIT_IMAGE,
        name="wit-conflux-delqueue",
        arguments=delqueue_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "wit-conflux-delqueue"},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": "512Mi",
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="wit-conflux-delqueue",
    )
    return delqueue


def k8s_makecsvs(dag):
    makecsvs_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-conflux image {image}"
            dea-conflux stack --parquet-path {{{{ dag_run.conf.get("intermediatedir", "{intermediatedir}") }}}} --output {{{{ dag_run.conf.get("csvdir", "{csvdir}") }}}} --mode wit_tooling
            """.format(
                image=CONFLUX_WIT_IMAGE,
                csvdir=DEFAULT_PARAMS['csvdir'],
                intermediatedir=DEFAULT_PARAMS['intermediatedir'],
            )
        ),
    ]
    makecsvs = KubernetesPodOperator(
        image=CONFLUX_WIT_IMAGE,
        name="wit-conflux-makecsvs",
        arguments=makecsvs_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "wit-conflux-makecsvs"},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": "512Mi",
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="wit-conflux-makecsvs",
    )
    return makecsvs


with dag:
    cmd = '{{{{ dag_run.conf.get("cmd", "{cmd}") }}}}'.format(
        cmd=DEFAULT_PARAMS['cmd'],
    )

    makecsvs = k8s_makecsvs(dag)

    for wit_input in WIT_INPUTS.items():
        product = wit_input['product']
        plugin = wit_input['plugin']
        queue = wit_input['queue']

        getids = k8s_getids(dag, cmd, product)
        makequeue = k8s_makequeue(dag, queue)
        push = k8s_queue_push(dag, queue, product + '-id.txt')
        task = k8s_job_task(dag, queue, plugin)
        delqueue = k8s_delqueue(dag, queue)

        getids >> makequeue >> push >> task >> delqueue >> makecsvs
