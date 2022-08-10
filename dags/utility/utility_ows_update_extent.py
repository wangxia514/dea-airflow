"""
# OWS update ranges Utility Tool (Self Serve)
This is utility is to provide administrators the easy accessiblity to run ad-hoc --views and update-ranges

## Note
All list of utility dags here: https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/utility, see Readme

## Customisation
The DAG can be parameterized with run time configuration `products`

To run with all, set `dag_run.conf.products` to `--all`
otherwise provide products to be refreshed seperated by space, i.e. `s2a_nrt_granule s2b_nrt_granule`
dag_run.conf format:

### sample conf in json format

    {
        "products": "--all"
    }

    or

    {
        "products": "s2a_nrt_granule s2b_nrt_granule"
    }

"""

from airflow import DAG
from textwrap import dedent

from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.utils.trigger_rule import TriggerRule

from dea_utils.update_ows_products import ows_update_operator
from infra.images import INDEXER_IMAGE
from infra.podconfig import (
    ONDEMAND_NODE_AFFINITY,
)
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    AWS_DEFAULT_REGION,
)
from datetime import datetime, timedelta

DAG_NAME = "utility_ows-update-extent"

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
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
}

S3_TO_DC_CMD = [
    "bash",
    "-c",
    dedent(
        """
        # Point to the internal API server hostname
        APISERVER=https://kubernetes.default.svc

        # Path to ServiceAccount token
        SERVICEACCOUNT=/var/run/secrets/kubernetes.io/serviceaccount

        # Read this Pod's namespace
        NAMESPACE=$(cat ${SERVICEACCOUNT}/namespace)

        # Read the ServiceAccount bearer token
        TOKEN=$(cat ${SERVICEACCOUNT}/token)

        # Reference the internal certificate authority (CA)
        CACERT=${SERVICEACCOUNT}/ca.crt

        # Explore the API with TOKEN
        curl --cacert ${CACERT} --header "Authorization: Bearer ${TOKEN}" -X GET ${APISERVER}/api

        curl --cacert ${CACERT} --header "Authorization: Bearer ${TOKEN}" -X GET ${APISERVER}/apis/apps/v1/namespaces/web/deployments
        """
    ),
]

# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "ows", "self-service"],
)

with dag:

    ows_update_operator(products="{{ dag_run.conf.products }}", dag=dag)

    REROLL_DEPLOYMENT = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "ows-deployment-restart"},
        service_account_name="ows-deployment-reroller",
        arguments=S3_TO_DC_CMD,
        name="datacube-index",
        task_id="reroll-pods",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
        trigger_rule=TriggerRule.NONE_FAILED_OR_SKIPPED,  # Needed in case add product was skipped
    )
