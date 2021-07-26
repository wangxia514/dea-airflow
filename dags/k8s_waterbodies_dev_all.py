"""
DEA Waterbodies processing on dev.

DAG to run the "all" workflow of DEA Waterbodies.
"""
from collections import OrderedDict
from datetime import datetime, timedelta
import json

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.operators.python_operator import BranchPythonOperator
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
import boto3
from botocore.handlers import disable_signing

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
    {
        "key": "dedicated",
        "operator": "Equal",
        "value": "waterbodies",
        "effect": "NoSchedule",
    }
]

MEM_BRANCHES = OrderedDict(
    [
        ("tiny", 512),
        ("small", 1024),
        ("large", 8 * 1024),
        ("huge", 64 * 1024),
        ("jumbo", 128 * 1024),
    ]
)

# This is the original waterbodies command:
# parallel --delay 5 --retries 3 --load 100%  --colsep ',' python -m dea_waterbodies.make_time_series ::: $CONFIG,--part,{1..24},--chunks,$NCHUNKS

# THE DAG
dag = DAG(
    "k8s_waterbodies_dev_all",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # triggered only
    catchup=False,
    concurrency=128,
    tags=["k8s", "landsat", "waterbodies"],
)


# def k8s_pod_task(mem, part, name):
#     """
#     method docstring
#     """
#     cmd = [
#         "bash",
#         "-c",
#         dedent(
#             """
#             echo "Using dea-waterbodies image {image}"
#             wget {conf} -O config.ini
#             cat config.ini

#             # Download xcom path to the IDs file.
#             echo "Downloading {{{{ ti.xcom_pull(task_ids='waterbodies-all-getchunks')['chunks_path'] }}}}"
#             aws s3 cp {{{{ ti.xcom_pull(task_ids='waterbodies-all-getchunks')['chunks_path'] }}}} ids.json

#             # Write xcom data to a TXT file.
#             python - << EOF
#             import json
#             with open('ids.json') as f:
#                 ids = json.load(f)
#             with open('ids.txt', 'w') as f:
#                 f.write('\\n'.join(ids['chunks'][{part}]['ids']))
#             EOF

#             # Execute waterbodies on the IDs.
#             echo "Processing:"
#             cat ids.txt
#             cat ids.txt | python -m dea_waterbodies.make_time_series --config config.ini
#             """.format(
#                 image=WATERBODIES_UNSTABLE_IMAGE, conf=config_path, part=part
#             )
#         ),
#     ]
#     req_mem = "{}Mi".format(int(mem))
#     return KubernetesPodOperator(
#         image=WATERBODIES_UNSTABLE_IMAGE,
#         name="waterbodies-all",
#         arguments=cmd,
#         image_pull_policy="IfNotPresent",
#         labels={"step": "waterbodies-" + name},
#         get_logs=True,
#         affinity=affinity,
#         is_delete_operator_pod=True,
#         resources={
#             "request_cpu": "1000m",
#             "request_memory": req_mem,
#         },
#         namespace="processing",
#         tolerations=tolerations,
#         task_id=name,
#     )


with dag:
    config_name = '{{ dag_run.conf.get("config_name", "config_moree_test_aws") }}'
    config_path = f"https://raw.githubusercontent.com/GeoscienceAustralia/dea-waterbodies/stable/ts_configs/{config_name}"

    # We need to download the DBF and do the chunking.
    # We will do this within a Kubernetes pod.
    n_chunks = 128
    getchunks_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-waterbodies image {image}"
            echo "Writing to /airflow/xcom/return.json"
            python -m dea_waterbodies.make_chunks {conf} {n_chunks} > /airflow/xcom/return.json
            """.format(
                image=WATERBODIES_UNSTABLE_IMAGE, conf=config_path, n_chunks=n_chunks
            )
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

    # Next we need to spawn a queue for each memory branch.
    queues = {}
    for branch in MEM_BRANCHES:
        # TODO(MatthewJA): Use the name/ID of this DAG
        # to make sure that we don't double-up if we're
        # running two DAGs simultaneously.
        queue_name = f'waterbodies-{branch}-sqs'
        makequeue_cmd = [
            "bash",
            "-c",
            dedent(
                """
                echo "Using dea-waterbodies image {image}"
                python -m dea_waterbodies.queues make {name}
                """.format(
                    image=WATERBODIES_UNSTABLE_IMAGE, name=queue_name,
                )
            ),
        ]
        makequeue = KubernetesPodOperator(
            image=WATERBODIES_UNSTABLE_IMAGE,
            name=f"waterbodies-all-makequeue-{branch}",
            arguments=makequeue_cmd,
            image_pull_policy="IfNotPresent",
            labels={"step": "waterbodies-dev-all-makequeue"},
            get_logs=True,
            affinity=affinity,
            is_delete_operator_pod=True,
            resources={
                "request_cpu": "1000m",
                "request_memory": "512Mi",
            },
            namespace="processing",
            tolerations=tolerations,
            task_id=f"waterbodies-all-makequeue-{branch}",
        )
        getchunks >> makequeue
        queues[branch] = makequeue

    # Now delete them.
    for branch in MEM_BRANCHES:
        # TODO(MatthewJA): Use the name/ID of this DAG
        # to make sure that we don't double-up if we're
        # running two DAGs simultaneously.
        queue_name = f'waterbodies-{branch}-sqs'
        delqueue_cmd = [
            "bash",
            "-c",
            dedent(
                """
                echo "Using dea-waterbodies image {image}"
                python -m dea_waterbodies.queues delete {name}
                """.format(
                    image=WATERBODIES_UNSTABLE_IMAGE, name=queue_name,
                )
            ),
        ]
        delqueue = KubernetesPodOperator(
            image=WATERBODIES_UNSTABLE_IMAGE,
            name=f"waterbodies-all-delqueue-{branch}",
            arguments=delqueue_cmd,
            image_pull_policy="IfNotPresent",
            labels={"step": "waterbodies-dev-all-delqueue"},
            get_logs=True,
            affinity=affinity,
            is_delete_operator_pod=True,
            resources={
                "request_cpu": "1000m",
                "request_memory": "512Mi",
            },
            namespace="processing",
            tolerations=tolerations,
            task_id=f"waterbodies-all-delqueue-{branch}",
        )
        queues[branch] >> delqueue
