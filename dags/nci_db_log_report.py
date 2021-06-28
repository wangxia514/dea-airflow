"""
# Archive NCI Database Logs and Upload PGBadger Report to S3

The DEA database servers at the NCI only keep the last 7 days of log files.

It would be useful to keep them for longer, or at the least, a historic summary.

This DAG uses a script on the NCI to transfer them to `/g/data/v10`


"""
from datetime import datetime, timedelta
from textwrap import dedent

from airflow import DAG
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook as AwsHook
from airflow.providers.ssh.operators.ssh import SSHOperator

from operators.ssh_operators import SecretHandlingSSHOperator
from infra.connections import AWS_NCI_DB_BACKUP_CONN

AWS_CONN_ID = AWS_NCI_DB_BACKUP_CONN

default_args = {
    "owner": "Damien Ayers",
    "depends_on_past": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(
        2021,
        2,
        23,
    ),
    "timeout": 60 * 60 * 2,  # For running SSH Commands
    "ssh_conn_id": "lpgs_gadi",
    "remote_host": "gadi-dm.nci.org.au",
    "email_on_failure": True,
    "email_on_retry": False,
    "email": "damien.ayers@ga.gov.au",
}

with DAG(
    "nci_db_log_report",
    default_args=default_args,
    catchup=False,
    schedule_interval="@daily",
    max_active_runs=1,
    tags=["nci"],
) as dag:
    COMMON = dedent(
        """
        set -euo pipefail
        module use /g/data/v10/public/modules/modulefiles
        module load dea

        cd /g/data/v10/agdc/pglogs/

        set -x
    """
    )

    # Requires GRANT EXECUTE ON FUNCTION pg_read_file(text,bigint,bigint) TO <service-user>;
    dump_daily_log = SSHOperator(
        task_id="dump_daily_log",
        command=COMMON
        + './pgcopy.sh {{ execution_date.format("%a") }}',  # %a is Short Day of Week
    )

    update_pg_badger_report = SSHOperator(
        task_id="update_pg_badger_report",
        command=COMMON + "pgbadger -I -O ${PWD}/reports/ logs/*",
    )

    aws_conn = AwsHook(aws_conn_id=AWS_CONN_ID, client_type="s3")
    upload_to_s3 = SecretHandlingSSHOperator(
        task_id="upload_to_s3",
        params=dict(aws_conn=aws_conn),
        secret_command="""
            {% set aws_creds = params.aws_conn.get_credentials() -%}

            export AWS_ACCESS_KEY_ID={{aws_creds.access_key}}
            export AWS_SECRET_ACCESS_KEY={{aws_creds.secret_key}}
        """,
        command=COMMON
        + "aws s3 sync report/ s3://nci-db-dump/pgbadger/nci/dea-db/ --no-progress",
    )

    dump_daily_log >> update_pg_badger_report >> upload_to_s3
