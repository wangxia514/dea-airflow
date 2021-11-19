"""
## Utility Tool (Self Serve)
For deleting datasets based on `datacube dataset search [conditions]`

#### Utility customisation
The DAG can be parameterized with run time configuration `dataset_search_query`

#### Utility customisation

#### example conf in json format

Use case 1: delete all datasets in a product

    {
        "dataset_search_query": "product=ga_s2_ba_provisional_3"
    }

Use case 2: delete datasets in a product at a certain time

    {
        "dataset_search_query": "product=ga_s2_ba_provisional_3 time in 2021-09-06"
    }

Use case 3: delete datasets in a product within a certain time

    {
        "dataset_search_query": "product=ga_s2_ba_provisional_3 time in [2021-09-06,  2021-09-08]"
    }

Use case 4: delete datasets in a product geolocation

    {
        "dataset_search_query": "product=ga_s2_ba_provisional_3 lat in [-40, -30]"
    }


Use case 5: delete a dataset based on id

    {
        "dataset_search_query": "id=81c5a2ac-606b-5e89-b302-0a82146af1fx"
    }

Use case 6: Any combination of `datacube dataset search query`

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from textwrap import dedent

from infra.images import INDEXER_IMAGE
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_WRITER_NAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
)
from infra.podconfig import (
    ONDEMAND_NODE_AFFINITY,
)

DAG_NAME = "deletion_utility_datasets"

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        # TODO: Pass these via templated params in DAG Run
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "DB_PORT": DB_PORT,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_ODC_WRITER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_WRITER_NAME, "postgres-password"),
    ],
}

DELETE_DATASETS_CMD = [
    "bash",
    "-c",
    dedent(
        """
        # get dataset ids
        datacube dataset search {{ dag_run.conf.dataset_search_query }} -f csv > /tmp/search_result.csv;

        # start sql execution
        PGPASSWORD=$DB_PASSWORD psql -d $DB_DATABASE -U $DB_USERNAME -h $DB_HOSTNAME <<EOF
        -- Error out if something goes wrong
        \\set ON_ERROR_STOP on

        BEGIN;
        CREATE TEMPORARY TABLE to_delete (
            id uuid,
            status varchar,
            product varchar,
            location varchar,
            primary key (id)
        );
        \\copy to_delete(id, status, product, location) FROM '/tmp/search_result.csv' DELIMITER ',' CSV HEADER;
        DELETE FROM agdc.dataset_location WHERE dataset_ref IN (SELECT id FROM to_delete);
        DELETE FROM agdc.dataset_source WHERE source_dataset_ref IN (SELECT id FROM to_delete);
        DELETE FROM agdc.dataset_source WHERE dataset_ref IN (SELECT id FROM to_delete);
        DELETE FROM agdc.dataset WHERE id IN (SELECT id FROM to_delete);
        end;
        EOF
        """
    ),
]

"""
"""

# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "dataset-deletion", "deletion", "self-service"],
)

with dag:

    DELETE_DATASETS = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "delete-datasets"},
        arguments=DELETE_DATASETS_CMD,
        name="delete-datasets",
        task_id="delete-datasets",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )
