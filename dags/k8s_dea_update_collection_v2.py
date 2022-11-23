# -*- coding: utf-8 -*-

"""
### DEA Access update collection

The collection updater is a manual run to trigger RESTO API collection update.

This should be done after any changes to the collections.csv in dea-config. e.g. Adding a new collection item or removing or updating

#### Docker image notes

`UPDATE_COLLECTION_IMAGE` image is built through github action workflow and published to ECR. The Dockerfile is located at `components/update-collectionr/Dockerfile` and part of a private repo `jjrom/dea-access` at this time.

#### Airflow dependencies

* A secret is used for the collection pods. This must exist under the namespace `processing`. The creation is currently controlled with the `datakube` repo. (*see core team for access*)

Environment variables for update-collection image are fed from the secrets

"""
from datetime import datetime, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

from airflow.kubernetes.secret import Secret

# Operators; we need this to operate!
from airflow.operators.bash import BashOperator

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
    "Collection Updater V2",
    doc_md=__doc__,
    default_args=default_args,
    description="Collection Updater V2",
    concurrency=1,
    max_active_runs=1,
    catchup=False,
    params={
        "DEFAULT_TIMEOUT": "45",  # seconds
        "RESTO_URL": "resto.dev.dea.ga.gov.au",
    },
    schedule_interval=None,
)
# [END instantiate_dag]

with pipeline:
    task_collection_updater = BashOperator(
        task_id="task_collection_updater",  # task_0_0_fc_percentile_albers_annual
        bash_command="echo $API_ADMIN_USERID",
    )