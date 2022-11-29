# -*- coding: utf-8 -*-

"""
### DEA Access Resto data ingester

The ingester is a manual run workflow to start the initial ingestion of collection products from the [explorer stac api](https://explorer.dea.ga.gov.au/stac) to the resto service.

Two health checks are made in the `pipeline` before queueing the collections for ingestion with the [KubernetesPodOperator()](https://airflow.apache.org/docs/stable/_api/airflow/contrib/operators/kubernetes_pod_operator/index.html).

#### Docker image notes

`STAC2RESTO_IMAGE` is built and pushed to ECR repo using github workflow action. The dockerfile is part of a private repository `jjrom/dea-access` at this time.

`CURL_SVC_IMAGE` is the [official docker image](https://hub.docker.com/r/curlimages/curl) for curl. Using todays (July 2020) latest release `curlimages/curl:7.71.1`

#### Airflow dependencies

* A secret is used for the collection pods. This must exist under the namespace `processing`. The creation is currently controlled with the `datakube` repo. (*see core team for access*)

#### Other notes

Current [retry policy](https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#module-urllib3.util.retry) is set as follows for the resto-stac2resto image.

* `total retries`: 3
* `backoff factor`: 2
* `http status retry forcelist`: 429, 500, 502, 503, 504
* `method whitelist`: HEAD, GET, POST
* `User-Agent`: dea-access-resto-ingester/v1

Environment variables for resto-stac2resto image that can be passed.

* `DEFAULT_TIMEOUT`: 25
* `DEVEL`: false
* `RESTO_AUTH`: user:some-random-password
* `RESTO_PROTOCOL`: https://
* `RESTO_URL`: resto.192.168.1.233.nip.io
* `SSL_VERIFY`: true
* `STAC_URL`: https://explorer.dea.ga.gov.au/collections
* `MAX_FEATURES`: 10 *items, can be set to limit feature ingestion for testing*

"""
from datetime import datetime, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

from airflow.kubernetes.secret import Secret

# Operators; we need this to operate!
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.operators.dummy_operator import DummyOperator
from infra.projects.dea_access import DEA_ACCESS_RESTO_API_ADMIN_SECRET

# [END import_module]

# [START default_args]
# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": datetime(2020, 7, 6),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret(
            "env",
            "API_ADMIN_USERID",
            DEA_ACCESS_RESTO_API_ADMIN_SECRET,
            "API_ADMIN_USERID",
        ),
        Secret(
            "env", "JWT_PASSPHRASE", DEA_ACCESS_RESTO_API_ADMIN_SECRET, "JWT_PASSPHRASE"
        ),
    ],
}
# [END default_args]

# Docker images
CURL_SVC_IMAGE = "curlimages/curl:7.71.1"
STAC2RESTO_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/dea-access/stac-to-resto:master"
)

# Set kubernetes secret
SECRET_ENV = Secret(
    deploy_type="env",
    # The name of the environment variable
    deploy_target="RESTO_AUTH",
    # Name of the Kubernetes Secret
    secret=DEA_ACCESS_RESTO_API_ADMIN_SECRET,
    # Key of a secret stored in this Secret object
    key="RESTO_AUTH",
)

SECRET_ENV_API_USERID = Secret(
    deploy_type="env",
    # The name of the environment variable
    deploy_target="API_ADMIN_USERID",
    # Name of the Kubernetes Secret
    secret=DEA_ACCESS_RESTO_API_ADMIN_SECRET,
    # Key of a secret stored in this Secret object
    key="API_ADMIN_USERID",
)

SECRET_ENV_JWT_PASSPHRASE = Secret(
    deploy_type="env",
    # The name of the environment variable
    deploy_target="JWT_PASSPHRASE",  # Name of the Kubernetes Secret
    secret=DEA_ACCESS_RESTO_API_ADMIN_SECRET,
    # Key of a secret stored in this Secret object
    key="JWT_PASSPHRASE",
)

# [START instantiate_dag]
pipeline = DAG(
    "k8s_dea_access_resto_ingester",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Access resto ingester",
    concurrency=8,
    max_active_runs=1,
    catchup=False,
    params={
        "DEFAULT_TIMEOUT": "45",  # seconds
        "ITAG_SVC_NAME": "dea-access-resto-service.web.svc.cluster.local",
        "RESTO_SVC_NAME": "dea-access-itag-service.web.svc.cluster.local",
        "RESTO_URL": "resto.dea.ga.gov.au",
    },
    schedule_interval=None,
)
# [END instantiate_dag]

with pipeline:

    # Check resto service is running.

    # [START task_http_resto_svc_sensor_check]
    task_http_resto_svc_sensor_check = KubernetesPodOperator(
        namespace="processing",
        name="dea-access-resto-svc-check",
        task_id="task_http_resto_svc_sensor_check",
        image_pull_policy="Always",
        image=CURL_SVC_IMAGE,
        is_delete_operator_pod=True,
        arguments=["--verbose", "http://{{ params.RESTO_SVC_NAME }}"],
        labels={"runner": "airflow"},
        resources={
            "request_cpu": "250m",
            "request_memory": "32Mi",
            "limit_cpu": "500m",
            "limit_memory": "64Mi",
        },
        get_logs=True,
    )

    # Check itag service is running.

    # [START task_http_resto_svc_sensor_check]
    task_http_itag_svc_sensor_check = KubernetesPodOperator(
        namespace="processing",
        name="dea-access-itag-svc-check",
        task_id="task_http_itag_svc_sensor_check",
        image_pull_policy="Always",
        image=CURL_SVC_IMAGE,
        is_delete_operator_pod=True,
        arguments=["--verbose", "http://{{ params.ITAG_SVC_NAME }}"],
        labels={"runner": "airflow"},
        resources={
            "request_cpu": "250m",
            "request_memory": "32Mi",
            "limit_cpu": "500m",
            "limit_memory": "64Mi",
        },
        get_logs=True,
    )

    # TODO: How do we check success? Keep as dummy manual checking for now.
    task_final_ingester_check = DummyOperator(task_id="task_final_ingester_check")

    # [START task_*_*_collection_id]
    ingester_task = KubernetesPodOperator(
        namespace="processing",
        name="dea-access-resto-ingester_v2",
        task_id="task_ingester",  # task_0_0_fc_percentile_albers_annual
        image_pull_policy="Always",
        image=STAC2RESTO_IMAGE,
        is_delete_operator_pod=True,  # clean pod
        labels={"runner": "airflow"},
        env_vars={
            "DEFAULT_TIMEOUT": "{{ params.DEFAULT_TIMEOUT }}",
            "RESTO_URL": "{{ params.RESTO_URL }}",
            "COLLECTION_LIST": "{{ params.PRODUCT }}",
        },
        secrets=[
            SECRET_ENV,
            SECRET_ENV_API_USERID,
            SECRET_ENV_JWT_PASSPHRASE,
        ],
        reattach_on_restart=True,
        resources={
            "request_cpu": "250m",
            "request_memory": "512Mi",
            "limit_cpu": "500m",
            "limit_memory": "1024Mi",
        },
        get_logs=True,
    )

    # [Setting up Dependencies]
    (
        [
            task_http_itag_svc_sensor_check, task_http_resto_svc_sensor_check
        ]
        >> ingester_task
    )
