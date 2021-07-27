"""
# Debugging Tool (Admin use)
## Test ssh operators
During airflow v2 upgrade, sshoperator issue was raised this dag was created for testing v1 airflow and v2 airflow ssh operator.

## Life span
Can be deleted after v2 upgrade is completed.
"""
from datetime import datetime, timedelta
from textwrap import dedent

import pendulum
from airflow import DAG

from airflow.contrib.operators.ssh_operator import SSHOperator as v1_SSHOperator
from infra.connections import AWS_DEA_PUBLIC_DATA_UPLOAD_CONN

from airflow.providers.ssh.operators.ssh import SSHOperator as v2_SSHOperator
from airflow.providers.ssh.hooks.ssh import SSHHook as v2_SSHHook  # noqa: F401


HOURS = 60 * 60
MINUTES = 60
DAYS = HOURS * 24
WORK_DIR = "/g/data/v10/work/s2_nbart_rolling_archive_dev"
SENTINEL_2_ARD_TOPIC_ARN = (
    "arn:aws:sns:ap-southeast-2:451924316694:dea-dev-eks-l2-nbart"
)
local_tz = pendulum.timezone("Australia/Canberra")
# language="Shell Script"

default_args = {
    "owner": "Pin Jin",
    "start_date": datetime(2021, 3, 1, tzinfo=local_tz),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email": "pin.jin@ga.gov.au",
    "ssh_conn_id": "lpgs_gadi",
    "aws_conn_id": AWS_DEA_PUBLIC_DATA_UPLOAD_CONN,
}
dag = DAG(
    dag_id="test_ssh_operators",
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    max_active_runs=4,
    default_view="tree",
    tags=["test", "SSHOPERATOR"],
)
with dag:
    # Uploading s2_to_s3_rolling.py script to NCI
    # language="Shell Script"
    v1_ls = v1_SSHOperator(
        task_id="test_v1_ssh_operator",
        # language="Shell Script"
        command=dedent(
            """
            ls
        """
        ),
        remote_host="gadi-dm.nci.org.au",
        timeout=20 * MINUTES,
    )

    v2_ls = v2_SSHOperator(
        task_id="test_v2_ssh_operator",
        # language="Shell Script"
        command=dedent(
            """
            ls
        """
        ),
        remote_host="gadi-dm.nci.org.au",
        timeout=20 * MINUTES,
    )
