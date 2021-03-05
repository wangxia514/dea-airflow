"""
# Archive NCI Database Logs and Upload PGBadger Report to S3

"""
from datetime import datetime, timedelta
from textwrap import dedent

import pendulum
from airflow import DAG
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.ssh_operator import SSHOperator

default_args = {
    'owner': 'Damien Ayers',
    'depends_on_past': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2021, 2, 23,),
    'timeout': 60 * 60 * 2,  # For running SSH Commands
    'ssh_conn_id': 'lpgs_gadi',
    'remote_host': 'gadi-dm.nci.org.au',
    'email_on_failure': True,
    'email_on_retry': False,
    'email': 'damien.ayers@ga.gov.au',
}

with DAG('nci_db_log_report',
         default_args=default_args,
         catchup=False,
         schedule_interval="@daily",
         max_active_runs=1,
         tags=['nci'],
         ) as dag:
    COMMON = dedent('''
        set -e
        module use /g/data/v10/public/modules/modulefiles
        module load dea

        cd /g/data/v10/agdc/pglogs/

        set -x
    ''')

    # Requires GRANT EXECUTE ON FUNCTION pg_read_file(text,bigint,bigint) TO <service-user>;
    dump_daily_log = SSHOperator(
        task_id='dump_daily_log',
        command=COMMON + dedent("""
            ./pgcopy.sh
        """),
    )

    update_pg_badger_report = SSHOperator(
        task_id='update_pg_badger_report',
        command=COMMON + dedent("""
            pgbadger -I -O ${PWD}/reports/ logs/*
        """),
    )

    aws_conn = AwsHook(aws_conn_id='aws_nci_db_backup')
    upload_to_s3 = SSHOperator(
        task_id='upload_to_s3',
        params=dict(aws_conn=aws_conn),
        command=COMMON + dedent('''
            {% set aws_creds = params.aws_conn.get_credentials() -%}
            
            export AWS_ACCESS_KEY_ID={{aws_creds.access_key}}
            export AWS_SECRET_ACCESS_KEY={{aws_creds.secret_key}}

            s3_dump_file=s3://nci-db-dump/prod/"${file_prefix}-datacube.pgdump"
            aws s3 cp "${file_prefix}-datacube.pgdump" "${s3_dump_file}" --no-progress

        ''')

    )
