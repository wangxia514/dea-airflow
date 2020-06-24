# -*- coding: utf-8 -*-

"""
### DEA Access dataloader

The dataloader is run weekly to update the Kuberneties (k8s) DEA Access elasticsearch container (egg), with the latest allCountries.zip from [geonames.org](https://download.geonames.org/export/dump/).

Two health checks are made in the `pipeline` before downloading the zip and attempting to update using the latest `allCountries.zip` file.

#### Purely for informational purposes

* `Branch`: NEMO
* `Division`: PSC
* `Section`: OPS

#### Docker image notes

`EGGLOADER_SVC_IMAGE` is build as part of the `dea-access-egg` service and is pushed to a private repo in AWS ECR (*see core team for access*). The Dockerfile is located at `components\egg\Dockerfile.loader` and part of a private repo `jjrom/dea-access` at this time. Updates to the `components\egg\Dockerfile.loader` file rebuilds and pushes the image to `538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/dea-access/egg-dataloader:latest`

`CURL_SVC_IMAGE` is the [official docker image](https://hub.docker.com/r/curlimages/curl) for curl. Using todays (June 2020) latest release `curlimages/curl:7.70.0`

#### Airflow dependencies

For the `HttpSensor` to work a new [connection](/admin/connection/new) is needed with the following settings.

* `Conn Id`: http_geonames_org
* `Conn Type `: HTTP
* `Host`: download.geonames.org
* `Schema `: https
* `Port`: 443
"""
from datetime import datetime, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

# Operators; we need this to operate!
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.sensors import HttpSensor

# [END import_module]

# [START default_args]
# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    'owner': 'Robert Gurtler',
    'depends_on_past': False,
    'start_date': datetime(2020, 6, 16),
    'email': ['robert.gurtler@ga.gov.au'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}
# [END default_args]

# Docker images
CURL_SVC_IMAGE = "curlimages/curl:7.70.0"
EGGLOADER_SVC_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/dea-access/egg-dataloader:latest"

# [START instantiate_dag]
pipeline = DAG(
    'k8s_dea_access_dataloader',
    doc_md=__doc__,
    default_args=default_args,
    description='DEA Access dataloader',
    concurrency=2,
    max_active_runs=1,
    catchup=False,
    params={
        'egg_svc_data_dir': '/data',
        'egg_svc_name': 'dea-access-egg-svc.web.svc.cluster.local',
        'geonames_endpoint': 'export/dump/allCountries.zip',
    },
    schedule_interval='30 1 * * 0',
    tags=['k8s', 'nemo', 'psc', 'egg'],
)
# [END instantiate_dag]

with pipeline:

    # [START task_http_geonames_org_sensor_check]
    task_http_geonames_org_sensor_check = HttpSensor(
        task_id='http_geonames_org_sensor_check',
        http_conn_id='http_geonames_org',
        endpoint='{{ params.geonames_endpoint }}',
        method='HEAD',
        response_check=lambda response: True if response.ok else False,
        poke_interval=2,
        # Extra options for the ‘requests’ library, see the ‘requests’ documentation (options to modify timeout, ssl, etc.)
        extra_options={
          'verify': False,
        },
    )

    # [START task_http_egg_svc_check]
    task_http_egg_svc_check = KubernetesPodOperator(
        namespace='processing',
        name='dea-access-egg-svc-check',
        task_id='http_egg_svc_sensor_check',
        image_pull_policy='IfNotPresent',
        image=CURL_SVC_IMAGE,
        is_delete_operator_pod=True,
        arguments=["--verbose", "http://{{ params.egg_svc_name }}:9200"],
        labels={
          'runner': 'airflow',
        },
        get_logs=True,
    )

    # [START task_dataloader]
    task_dataloader = KubernetesPodOperator(
        namespace='processing',
        name="dea-access-dataloader",
        task_id='dataloader',
        image_pull_policy='IfNotPresent',
        image=EGGLOADER_SVC_IMAGE,
        is_delete_operator_pod=True,
        labels={
          'runner': 'airflow',
        },
        env_vars={
          'DATA_DIR': '{{ params.egg_svc_data_dir }}',
          'ELASTIC_SCHEME': 'http',
          'ELASTIC_HOST': '{{ params.egg_svc_name }}',
          'ELASTIC_PORT': '9200',
          'GEONAMES_SRC': 'https://download.geonames.org/{{ params.geonames_endpoint }}',
        },
        get_logs=True,
    )

    # [Setting up Dependencies]
    [task_http_geonames_org_sensor_check, task_http_egg_svc_check] >> task_dataloader
