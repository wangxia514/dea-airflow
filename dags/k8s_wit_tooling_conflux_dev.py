"""
DEA WIT tooling Dev processing using Conflux.

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

use_id
    The unique use_id in shapefile.

"""
from datetime import datetime, timedelta
import logging

from airflow import DAG
from airflow_kubernetes_job_operator.kubernetes_job_operator import (
    KubernetesJobOperator,
)  # noqa: E501
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from textwrap import dedent

from infra.variables import (
    DB_DATABASE,
    DB_READER_HOSTNAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
    WIT_DEV_USER_SECRET,
    SECRET_ODC_READER_NAME,
)

# Default config parameters.
DEFAULT_PARAMS = dict(
    shapefile="s3://dea-public-data-dev/projects/WIT/test_shp/conflux_wb_Npolygons/wb_3_v2_conflux_10_test.shp",
    intermediatedir="s3://dea-public-data-dev/projects/WIT/test_result/test_10_polygons_09062022/timestamp_base_result",
    cmd="'time in [2000-01-01, 2010-01-01] lat in [-30, -29] lon in [141, 143] gqa_mean_x in [-1, 1]'",
    csvdir="s3://dea-public-data-dev/projects/WIT/test_result/test_10_polygons_09062022/polygon_base_result",
    use_id="uid",
)

# Requested memory. Memory limit is twice this.
CONFLUX_POD_MEMORY_MB = 40000

EC2_NUM = 1

CONFLUX_WIT_IMAGE = "geoscienceaustralia/dea-conflux:latest"

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
            WIT_DEV_USER_SECRET,
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            WIT_DEV_USER_SECRET,
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
    "retries": 64,
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
                                "r5-4xl-wit-tooling",
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
        "value": "wit_tooling",
        "effect": "NoSchedule",
    }
]


def print_configuration_function(ds, **context):
    """Print the configuration of this DAG"""
    logging.info("Running Configurations:")
    logging.info("dag_run:               " + context['params'])
    logging.info("ds:                    " + str(ds))
    logging.info("EC2_NUM:               " + str(EC2_NUM))
    logging.info("CONFLUX_POD_MEMORY_MB: " + str(CONFLUX_POD_MEMORY_MB))
    logging.info("")


# THE DAG
dag = DAG(
    "k8s_wit_conflux_dev",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # triggered only
    catchup=False,
    concurrency=128,
    tags=["k8s", "landsat", "wit", "conflux", "Work In Progress"],
)

# just keep the ls5 to save the development cost
WIT_INPUTS = [{"product": "ga_ls5t_ard_3", "plugin": "wit_ls5", "queue": "wit_conflux_ls5_integration_test_sqs"},
              {"product": "ga_ls7e_ard_3", "plugin": "wit_ls7", "queue": "wit_conflux_ls7_integration_test_sqs"},
              {"product": "ga_ls8c_ard_3", "plugin": "wit_ls8", "queue": "wit_conflux_ls8_integration_test_sqs"}]


def k8s_job_filter_task(dag, input_queue_name, output_queue_name, use_id):

    # we are using r5.4xl EC2: 16 CPUs + 128 GB RAM
    mem = CONFLUX_POD_MEMORY_MB // 2  # the biggest filter usage is 20GB
    req_mem = "{}Mi".format(int(mem))
    lim_mem = "{}Mi".format(int(mem))

    # 1. Each WIT EC2 can run 6 filter pod;
    # 2. and EC2_NUM == how many EC2
    # 3. there are 3 products
    # so each product filter parallelism = EC2_NUM * 6 / 3
    # => EC2_NUM * 2
    parallelism = EC2_NUM * 2
    cpu = 2
    cpu_request = f"{cpu}000m"  # 128/20 ~= 6, 16/6 ~= 2

    yaml = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": "filter-job",
                     "namespace": "processing"},
        "spec": {
            "parallelism": parallelism,
            "backoffLimit": 32,
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
                                    "cpu": cpu_request,
                                    "memory": req_mem,
                                },
                                "limits": {
                                    "cpu": cpu_request,
                                    "memory": lim_mem,
                                },
                            },
                            "command": ["/bin/bash"],
                            "args": [
                                "-c",
                                dedent(
                                    """
                                    dea-conflux filter-from-queue -v \
                                        --input-queue {input_queue_name} \
                                        --output-queue {output_queue_name} \
                                        --shapefile {{{{ dag_run.conf.get("shapefile", "{shapefile}") }}}} \
                                        --num-worker {cpu} \
                                        --use-id {use_id}
                                    """.format(input_queue_name=input_queue_name,
                                               output_queue_name=output_queue_name,
                                               shapefile=DEFAULT_PARAMS['shapefile'],
                                               cpu=cpu,
                                               use_id=use_id,
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
                                            "name": WIT_DEV_USER_SECRET,
                                            "key": "AWS_ACCESS_KEY_ID",
                                        },
                                    },
                                },
                                {
                                    "name": "AWS_SECRET_ACCESS_KEY",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": WIT_DEV_USER_SECRET,
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
        task_id="filter",
        get_logs=False,
        body=yaml,
    )
    return job_task


def k8s_job_run_wit_task(dag, queue_name, plugin, use_id):

    mem = CONFLUX_POD_MEMORY_MB
    req_mem = "{}Mi".format(int(mem))
    lim_mem = "{}Mi".format(int(mem))

    # 1. Each WIT EC2 can run 3 processing pod;
    # 2. and EC2_NUM == how many EC2;
    # 3. there are 3 products;
    # so each product parallelism = EC2_NUM * 3 / 3
    parallelism = EC2_NUM

    yaml = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": "processing-job",
                     "namespace": "processing"},
        "spec": {
            "parallelism": parallelism,
            "backoffLimit": 32,
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
                                    "cpu": "4000m",
                                    "memory": req_mem,
                                },
                                "limits": {
                                    "cpu": "4000m",
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
                                            --no-db \
                                            --shapefile {{{{ dag_run.conf.get("shapefile", "{shapefile}") }}}} \
                                            --output {{{{ dag_run.conf.get("intermediatedir", "{intermediatedir}") }}}} {{{{ dag_run.conf.get("flags", "") }}}} \
                                            --not-dump-empty-dataframe \
                                            --timeout 7200 \
                                            --use-id {use_id}
                                    """.format(queue=queue_name,
                                               shapefile=DEFAULT_PARAMS['shapefile'],
                                               intermediatedir=DEFAULT_PARAMS['intermediatedir'],
                                               plugin=plugin,
                                               use_id=use_id,
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
                                            "name": WIT_DEV_USER_SECRET,
                                            "key": "AWS_ACCESS_KEY_ID",
                                        },
                                    },
                                },
                                {
                                    "name": "AWS_SECRET_ACCESS_KEY",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": WIT_DEV_USER_SECRET,
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
        task_id="run",
        get_logs=False,
        body=yaml,
    )
    return job_task


def k8s_queue_push(dag, queue_name, filename, task_id):
    cmd = [
        "bash",
        "-c",
        dedent(
            """
            # Download the IDs file from xcom.
            echo "Downloading {{{{ ti.xcom_pull(task_ids='{task_id}')['ids_path'] }}}}"
            aws s3 cp {{{{ ti.xcom_pull(task_ids='{task_id}')['ids_path'] }}}} {filename}

            # Push the IDs to the queue.
            dea-conflux push-to-queue --txt {filename} --queue {queue}
            """.format(
                queue=queue_name,
                filename=filename,
                task_id=task_id,
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
        task_id="push",
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
        task_id="getids",
    )
    return getids


def k8s_makequeues(dag, raw_queue_name, final_queue_name):
    # TODO(MatthewJA): Use the name/ID of this DAG
    # to make sure that we don't double-up if we're
    # running two DAGs simultaneously.
    makequeue_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-conflux image {image}"
            dea-conflux make {raw_queue_name} --timeout 7200 --retries 1
            dea-conflux make {final_queue_name} --timeout 7200 --retries 1
            """.format(
                image=CONFLUX_WIT_IMAGE,
                raw_queue_name=raw_queue_name,
                final_queue_name=final_queue_name,
            )
        ),
    ]
    makequeue = KubernetesPodOperator(
        image=CONFLUX_WIT_IMAGE,
        name="wit-cconflux-makequeue",
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
        task_id="makequeue",
    )
    return makequeue


def k8s_delqueues(dag, raw_queue_name, final_queue_name):
    # TODO(MatthewJA): Use the name/ID of this DAG
    # to make sure that we don't double-up if we're
    # running two DAGs simultaneously.
    delqueue_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-conflux image {image}"
            dea-conflux delete {raw_queue_name}
            dea-conflux delete {final_queue_name}
            """.format(
                image=CONFLUX_WIT_IMAGE,
                raw_queue_name=raw_queue_name,
                final_queue_name=final_queue_name,
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
        task_id="delqueue",
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
    # we are using r5.4xlarge to run WIT. It has 16vCPU, and 128GB RAM.
    makecsvs = KubernetesPodOperator(
        image=CONFLUX_WIT_IMAGE,
        name="wit-conflux-makecsvs",
        arguments=makecsvs_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "wit-conflux-makecsvs"},
        get_logs=False,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "8000m",
            "request_memory": "60000Mi",
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="makecsvs",
    )
    return makecsvs


with dag:
    cmd = '{{{{ dag_run.conf.get("cmd", "{cmd}") }}}}'.format(
        cmd=DEFAULT_PARAMS['cmd'],
    )

    print_configuration = PythonOperator(
        task_id="print_configuration",
        python_callable=print_configuration_function,
        provide_context=True,
        dag=dag,
    )

    use_id = '{{{{ dag_run.conf.get("use_id", "{use_id}") }}}}'.format(
        use_id=DEFAULT_PARAMS['use_id'],
    )

    makecsvs = k8s_makecsvs(dag)

    for wit_input in WIT_INPUTS:
        product = wit_input['product']
        plugin = wit_input['plugin']
        queue = wit_input['queue']

        raw_queue_name = f"{queue}_raw"
        final_queue_name = queue

        with TaskGroup(group_id=f"wit-conflux-{plugin}") as tg:
            getids = k8s_getids(dag, cmd, product)
            makeprequeues = k8s_makequeues(dag, raw_queue_name, final_queue_name)
            push = k8s_queue_push(dag, raw_queue_name, f"{product}-id.txt", f"wit-conflux-{plugin}.getids")
            filter = k8s_job_filter_task(dag, input_queue_name=raw_queue_name, output_queue_name=final_queue_name, use_id=use_id)
            processing = k8s_job_run_wit_task(dag, final_queue_name, plugin, use_id)
            delprequeues = k8s_delqueues(dag, raw_queue_name, final_queue_name)

            getids >> makeprequeues >> push >> filter >> processing >> delprequeues

        print_configuration >> tg >> makecsvs
