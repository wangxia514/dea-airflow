"""
# S3 to Datacube Indexing

DAG to run indexing for Sentinel-2 data on S3 into AWS DB.

This DAG takes following input parameters from `"k8s_index_s2_s3_config"` variable:

 * `start_date`: Start date for DAG run.
 * `end_date`: End date for DAG run.
 * `catchup`: Set to "True" for back fill else "False".
 * `schedule_interval`: Set "" for no schedule else provide schedule cron or preset (@once, @daily).
 * `db_hostname`: Provide DB Host Name.
 * `db_database`: Provide DB Name.
 * `aws_iam_role`: Provide AWS IAM ROLE.
 * `s3bucket`: Name of the S3 bucket.

**EXAMPLE** *- Variable in JSON format with key name "k8s_index_s2_s3_config":*

    {
        "k8s_index_s2_s3_config":
        {
            "start_date": "2020-4-1",
            "end_date": "2020-4-30",
            "catchup": "False",
            "schedule_interval" : "@daily",
            "db_hostname": "database-write.local",
            "db_database": "ows-index",
            "aws_iam_role": "svc-dea-dev-eks-processing-index",
            "s3bucket": "dea-public-data-dev"
        }
    }
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.contrib.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator


# Read and load variable into dict
VARIABLE_NAME = "k8s_index_s2_s3_config"
dag_config = Variable.get(VARIABLE_NAME, deserialize_json=True)


def get_parameter_value_from_variable(_dag_config, parameter_name, default_value=''):
    """
    Return parameter value from variable
    :param _dag_config: Name of the variable
    :param parameter_name: Parameter name
    :param default_value: Default value if parameter is empty
    :return: Parameter value for provided parameter name
    """
    if parameter_name in _dag_config and _dag_config[parameter_name]:
        parameter_value = _dag_config[parameter_name]
    elif default_value != '':
        parameter_value = default_value
    else:
        raise Exception("Missing necessary parameter '{}' in "
                        "variable '{}'".format(parameter_name, VARIABLE_NAME))
    return parameter_value


DEFAULT_ARGS = {
    "owner": "Sachit Rajbhandari",
    "depends_on_past": False,
    "start_date": get_parameter_value_from_variable(dag_config, 'start_date', datetime.today()),
    "end_date": get_parameter_value_from_variable(dag_config, 'end_date', None),
    "email": ["sachit.rajbhandari@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        "DB_HOSTNAME": get_parameter_value_from_variable(dag_config, 'db_hostname'),
        "DB_DATABASE": get_parameter_value_from_variable(dag_config, 'db_database'),
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube
    "secrets": [
        Secret("env", "DB_USERNAME", "ows-db", "postgres-username"),
        Secret("env", "DB_PASSWORD", "ows-db", "postgres-password"),
    ],
    "params": {
        "s3bucket": get_parameter_value_from_variable(dag_config, 's3bucket'),
        "aws_iam_role": get_parameter_value_from_variable(dag_config, 'aws_iam_role'),
    }
}

INDEXER_IMAGE = "opendatacube/datacube-index:0.0.5"
EXPLORER_IMAGE = "opendatacube/dashboard:2.1.6"

dag = DAG(
    "k8s_index_s2_s3",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=get_parameter_value_from_variable(dag_config, 'catchup', False),
    schedule_interval=get_parameter_value_from_variable(dag_config, 'schedule_interval', None),
    tags=['k8s', 'sentinel_2']
)


with dag:

    # TODO: Bootstrap if targeting a Blank DB
    # TODO: Initialize Datacube
    # TODO: Add metadata types
    # TODO: Add products
    BOOTSTRAP = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        cmds=["datacube", "product", "list"],
        labels={"step": "bootstrap"},
        name="odc-bootstrap",
        task_id="bootstrap-task",
        get_logs=True,
    )

    ADD_PRODUCT = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        cmds=["datacube", "product", "add"],
        arguments=[
            "https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/"
            "9c12bb30bff1f81ccd2a94e2c5052288688c55d1/products/ga_s2_ard_nbar/ga_s2_ard_nbar_granule.yaml"
        ],
        labels={"step": "add-product"},
        name="odc-add-product",
        task_id="add-product-task",
        get_logs=True,
    )

    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        cmds=["s3-to-dc"],
        # Assume kube2iam role via annotations
        # TODO: Pass this via DAG parameters
        annotations={"iam.amazonaws.com/role": "{{ params.aws_iam_role }}"},
        # TODO: Collect form JSON used to trigger DAG
        arguments=[
            "s3://{{ params.s3bucket }}"
            "/L2/sentinel-2-nbar/S2MSIARD_NBAR/{{ yesterday_ds }}/*/*.yaml",
            "ga_s2a_ard_nbar_granule",
            "ga_s2b_ard_nbar_granule",
        ],
        labels={"step": "s3-to-rds"},
        name="datacube-index",
        task_id="indexing-task",
        get_logs=True,
    )

    BOOTSTRAP >> ADD_PRODUCT
    ADD_PRODUCT >> INDEXING
