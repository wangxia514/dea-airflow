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


def branch_mem(part, **kwargs):
    """
    method docstring
    """
    chunk_path_json = kwargs["ti"].xcom_pull(
        task_ids="waterbodies-all-getchunks", key="return_value"
    )
    chunks_path = chunk_path_json["chunks_path"]
    split = chunks_path.split("/")
    bucket = split[2]
    path = "/".join(split[3:])
    s3 = boto3.resource("s3")
    s3.meta.client.meta.events.register("choose-signer.s3.*", disable_signing)
    # Download the JSON
    print("Downloading", path, "from bucket", bucket)
    s3.Bucket(bucket).download_file(path, "chunks.json")
    with open("chunks.json") as f:
        chunk_json = json.load(f)
    assert 0 <= part < len(chunk_json["chunks"])
    part_details = chunk_json["chunks"][part]
    max_mem = float(part_details["max_mem_Mi"])
    print(f"Part {part} wants {max_mem}")
    for name, val in MEM_BRANCHES.items():
        if max_mem < val:
            return f"process-{part}-{name}"
    raise NotImplementedError("No branch with sufficient resources.")


def k8s_pod_task(mem, part, name):
    """
    method docstring
    """
    cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-waterbodies image {image}"
            wget {conf} -O config.ini
            cat config.ini

            # Download xcom path to the IDs file.
            echo "Downloading {{{{ ti.xcom_pull(task_ids='waterbodies-all-getchunks')['chunks_path'] }}}}"
            aws s3 cp {{{{ ti.xcom_pull(task_ids='waterbodies-all-getchunks')['chunks_path'] }}}} ids.json

            # Write xcom data to a TXT file.
            python - << EOF
            import json
            with open('ids.json') as f:
                ids = json.load(f)
            with open('ids.txt', 'w') as f:
                f.write('\\n'.join(ids['chunks'][{part}]['ids']))
            EOF

            # Execute waterbodies on the IDs.
            echo "Processing:"
            cat ids.txt
            cat ids.txt | python -m dea_waterbodies.make_time_series --config config.ini
            """.format(
                image=WATERBODIES_UNSTABLE_IMAGE, conf=config_path, part=part
            )
        ),
    ]
    req_mem = "{}Mi".format(int(mem))
    return KubernetesPodOperator(
        image=WATERBODIES_UNSTABLE_IMAGE,
        name="waterbodies-all",
        arguments=cmd,
        image_pull_policy="IfNotPresent",
        labels={"step": "waterbodies-" + name},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": req_mem,
        },
        namespace="processing",
        tolerations=tolerations,
        task_id=name,
    )


with dag:
    config_name = '{{ dag_run.conf.get("config_name", "config_moree_test_aws") }}'
    config_path = f"https://raw.githubusercontent.com/GeoscienceAustralia/dea-waterbodies/stable/ts_configs/{config_name}"

    # Now we need to download the DBF and do the chunking.
    # We will do this within a Kubernetes pod.
    n_chunks = 128
    getchunks_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-waterbodies image {image}"
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

    for part in range(n_chunks):
        # Set up the branching.
        branch = BranchPythonOperator(
            task_id=f"branch-mem-{part}",
            python_callable=branch_mem,
            provide_context=True,
            dag=dag,
            op_kwargs={"part": part},
        )
        getchunks >> branch

        # Then create the branch target operators.
        for name, val in MEM_BRANCHES.items():
            op = k8s_pod_task(val, part, f"process-{part}-{name}")
            branch >> op
