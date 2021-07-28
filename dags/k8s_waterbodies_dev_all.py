"""
DEA Waterbodies processing on dev.

DAG to run the "all" workflow of DEA Waterbodies.
"""
from collections import OrderedDict
from datetime import datetime, timedelta
# import json

from airflow import DAG
from airflow_kubernetes_job_operator.kubernetes_job_operator import KubernetesJobOperator  # noqa: E501
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

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

lower_mem_branches = {'tiny': 0}
for branch_low, branch_high in zip(MEM_BRANCHES, list(MEM_BRANCHES)[1:]):
    lower_mem_branches[branch_high] = MEM_BRANCHES[branch_low]

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


def k8s_queueread(dag, branch):
    """K8s operator for reading out the queue, for testing/dev use."""
    cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-waterbodies image {image}"

            # Do everything in Python.
            python - << EOF
            import boto3
            sqs = boto3.resource('sqs')
            name = '{queue}'
            queue = sqs.get_queue_by_name(QueueName=name)
            queue_url = queue.url

            while True:
                messages = queue.receive_messages(
                    AttributeNames=['All'],
                    MaxNumberOfMessages=1,
                )
                if len(messages) == 0:
                    break

                entries = [
                    {{'Id': msg.message_id,
                    'ReceiptHandle': msg.receipt_handle}}
                    for msg in messages
                ]

                print([msg.body for msg in messages])

                resp = queue.delete_messages(
                        QueueUrl=queue_url, Entries=entries,
                    )

                if len(resp['Successful']) != len(entries):
                    raise RuntimeError(
                        f"Failed to delete messages: {{entries}}"
                    )
            EOF
            """.format(
                image=WATERBODIES_UNSTABLE_IMAGE,
                queue=f'waterbodies_{branch}_sqs',
            )
        ),
    ]
    return KubernetesPodOperator(
        image=WATERBODIES_UNSTABLE_IMAGE,
        dag=dag,
        name=f"waterbodies-all-queueread-{branch}",
        arguments=cmd,
        image_pull_policy="IfNotPresent",
        labels={"step": "waterbodies-all-queueread"},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": '512Mi',
        },
        namespace="processing",
        tolerations=tolerations,
        task_id=f'waterbodies-all-queueread-{branch}',
    )


def k8s_job_task(dag, branch, config_path):
    mem = MEM_BRANCHES[branch]
    req_mem = "{}Mi".format(int(mem))
    lim_mem = "{}Mi".format(int(mem) * 2 if branch != 'jumbo' else int(mem))
    yaml = {
        'apiVersion': 'batch/v1',
        'kind': 'Job',
        'metadata': {
            'name': 'waterbodies-all-job',
            'namespace': 'processing'},
        'spec': {
            'parallelism': 64,  # TODO(MatthewJA): Make dynamic?
            'backoffLimit': 3,
            'template': {
                'spec': {
                    'restartPolicy': 'OnFailure',
                    'tolerations': tolerations,
                    'affinity': affinity,
                    'containers': [{
                        'name': 'waterbodies',
                        'image': WATERBODIES_UNSTABLE_IMAGE,
                        'imagePullPolicy': 'IfNotPresent',
                        'resources': {
                                "requests": {
                                    'cpu': "1000m",
                                    'memory': req_mem,
                                },
                                "limits": {
                                    'cpu': "2000m",
                                    'memory': lim_mem,
                                },
                            },
                        'command': ['/bin/bash'],
                        'args': [
                            '-c',
                            dedent(
                                """
                                echo "Retrieving $config_path"
                                wget {config} -O config.ini
                                cat config.ini

                                # Execute waterbodies on the IDs.
                                python -m dea_waterbodies.make_time_series --config config.ini --from-queue {queue}
                                """.format(queue=f'waterbodies_{branch}_sqs',
                                           config=config_path)
                            )
                        ]},
                    ],
                },
            },
        },
    }

    job_task = KubernetesJobOperator(
        image=WATERBODIES_UNSTABLE_IMAGE,
        dag=dag,
        name=f"waterbodies-all-{branch}-run",
        task_id=f"waterbodies-all-{branch}-run",
        get_logs=True,
        body=yaml,
    )
    return job_task


def k8s_queue_push(dag, branch):
    cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-waterbodies image {image}"

            # Download the IDs file from xcom.
            echo "Downloading {{{{ ti.xcom_pull(task_ids='waterbodies-all-getchunks')['chunks_path'] }}}}"
            aws s3 cp {{{{ ti.xcom_pull(task_ids='waterbodies-all-getchunks')['chunks_path'] }}}} ids.json

            # Write xcom data to a TXT file.
            python - << EOF
            import json
            with open('ids.json') as f:
                ids = json.load(f)
            all_ids = []
            for part in ids['chunks']:
                if {low} <= part['max_mem_Mi'] < {high}:
                    all_ids.extend(part['ids'])
            with open('ids.txt', 'w') as f:
                f.write('\\n'.join(all_ids))
            EOF

            # Push the IDs to the queue.
            aws sqs get-queue-url --queue-name {queue} --output text > queue.txt
            cat queue.txt
            queue_url=$(<queue.txt)
            cat ids.txt | xargs -L1 -I{{}} aws sqs send-message --queue-url $queue_url --message-body {{}}
            """.format(
                image=WATERBODIES_UNSTABLE_IMAGE,
                low=lower_mem_branches[branch],
                high=MEM_BRANCHES[branch],
                queue=f'waterbodies_{branch}_sqs',
            )
        ),
    ]
    return KubernetesPodOperator(
        image=WATERBODIES_UNSTABLE_IMAGE,
        dag=dag,
        name=f"waterbodies-all-push-{branch}",
        arguments=cmd,
        image_pull_policy="IfNotPresent",
        labels={"step": "waterbodies-push"},
        get_logs=True,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": '512Mi',
        },
        namespace="processing",
        tolerations=tolerations,
        task_id=f'waterbodies-all-push-{branch}',
    )


def k8s_getchunks(dag, n_chunks, config_path):
    """K8s pod operator to get chunks."""
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
    return getchunks


def k8s_makequeue(dag, branch):
    # TODO(MatthewJA): Use the name/ID of this DAG
    # to make sure that we don't double-up if we're
    # running two DAGs simultaneously.
    queue_name = f'waterbodies_{branch}_sqs'
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
    return makequeue


def k8s_delqueue(dag, branch):
    # TODO(MatthewJA): Use the name/ID of this DAG
    # to make sure that we don't double-up if we're
    # running two DAGs simultaneously.
    queue_name = f'waterbodies_{branch}_sqs'
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
    return delqueue


with dag:
    config_name = '{{ dag_run.conf.get("config_name", "config_moree_test_aws") }}'
    config_path = f"https://raw.githubusercontent.com/GeoscienceAustralia/dea-waterbodies/stable/ts_configs/{config_name}"

    # Download the DBF and do the chunking.
    n_chunks = 128
    getchunks = k8s_getchunks(dag, n_chunks, config_path)

    for branch in MEM_BRANCHES:
        # Next we need to spawn a queue for each memory branch.
        makequeue = k8s_makequeue(dag, branch)
        # Populate the queues.
        push = k8s_queue_push(dag, branch)
        # Now we'll do the main task.
        task = k8s_job_task(dag, branch, config_path)
        # Finally delete the queue.
        delqueue = k8s_delqueue(dag, branch)
        getchunks >> makequeue >> push >> task >> delqueue
