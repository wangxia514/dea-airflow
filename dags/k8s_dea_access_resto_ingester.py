# -*- coding: utf-8 -*-

"""
### DEA Access Resto data ingester

The ingester is a manual run workflow to start the initial ingestion of collection products from the [explorer stac api](https://explorer.dea.ga.gov.au/stac) to the resto service.

Two health checks are made in the `pipeline` before queueing the collections for ingestion with the [KubernetesPodOperator()](https://airflow.apache.org/docs/stable/_api/airflow/contrib/operators/kubernetes_pod_operator/index.html).

#### Purely for informational purposes

* `Branch`: NEMO
* `Division`: PSC
* `Section`: OPS

#### Docker image notes

`STAC2RESTO_IMAGE` is build manual and pushed to public repo. The Dockerfile is located at `airflow\Dockerfile.stac2resto` and part of a private repo `jjrom/dea-access` at this time.

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
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.dummy_operator import DummyOperator
from infra.variables import DEA_ACCESS_RESTO_API_ADMIN_SECRET
import requests
import csv
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
         Secret("env", "API_ADMIN_USERID", DEA_ACCESS_RESTO_API_ADMIN_SECRET, "API_ADMIN_USERID"),
         Secret("env", "JWT_PASSPHRASE", DEA_ACCESS_RESTO_API_ADMIN_SECRET, "JWT_PASSPHRASE"),
     ],
}
# [END default_args]

# Docker images
CURL_SVC_IMAGE = "curlimages/curl:7.71.1"
STAC2RESTO_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/dea-access/stac-to-resto:latest"

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
    deploy_target="JWT_PASSPHRASE", # Name of the Kubernetes Secret
    secret=DEA_ACCESS_RESTO_API_ADMIN_SECRET,
    # Key of a secret stored in this Secret object
    key="JWT_PASSPHRASE",
)

# Collection items to be loaded into resto service from explorer.dea.ga.gov.au/collections
# TODO: Investigate if this can be fetched from a google doc and loaded with XCom (maybe),
#       OPS could then just update a google doc and start the pipeline.
#read from github dea-config the latest csv file
url = 'https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/develop/workspaces/collections.csv'
r = requests.get(url, allow_redirects=True)

#read the name and the count columns
open('collections.csv', 'wb').write(r.content)
with open('collections.csv', 'rt') as csvfile:
    # get number of columns
    for line in csvfile.readlines():
       array = line.split(',')
    
    num_columns = len(array)
    csvfile.seek(0)
    reader = csv.reader(csvfile, delimiter=',')
    next(reader, None)  # skip the headers
    included_cols = [5]
    COLLECTIONS_LIST = []
    for row in reader:
       if row[5] != 'None':
          COLLECTIONS_LIST.append(row[5])

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
        "RESTO_URL": "resto.dev.dea.ga.gov.au",
    },
    schedule_interval=None,
    tags=["k8s", "nemo", "psc", "resto"],
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

    # Prepare for dynamic task generation

    # Split COLLECTIONS_LIST into four chunks.
    split_list = 4
    tasks_list = [
        COLLECTIONS_LIST[i : i + split_list]
        for i in range(0, len(COLLECTIONS_LIST), split_list)
    ]
    tasks_length = len(tasks_list)

    # Beginning placeholder for KubernetesPodOperator() tasks
    all_ingester_tasks = {}

    # Work through the top level tasks_list items
    for index in range(tasks_length):
        # Add to all_ingester_tasks if missing
        if index not in all_ingester_tasks:
            # Work through the tasks_list sub lists
            for idx, collection in enumerate(tasks_list[index]):

                # Let's create some KubernetesPodOperator() tasks

                # [START task_*_*_collection_id]
                all_ingester_tasks[index] = KubernetesPodOperator(
                    namespace="processing",
                    name="dea-access-resto-ingester",
                    task_id=f"task_{index}_{idx}_{collection}",  # task_0_0_fc_percentile_albers_annual
                    image_pull_policy="Always",
                    image=STAC2RESTO_IMAGE,
                    is_delete_operator_pod=True,  # clean pod
                    labels={"runner": "airflow"},
                    env_vars={
                        "DEFAULT_TIMEOUT": "{{ params.DEFAULT_TIMEOUT }}",
                        "RESTO_URL": "{{ params.RESTO_URL }}",
                        "COLLECTION_LIST": collection,
                    },
                    secrets=[SECRET_ENV,SECRET_ENV_API_USERID,SECRET_ENV_JWT_PASSPHRASE],
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
                [
                    task_http_itag_svc_sensor_check,
                    task_http_resto_svc_sensor_check,
                ] >> all_ingester_tasks[index] >> task_final_ingester_check
