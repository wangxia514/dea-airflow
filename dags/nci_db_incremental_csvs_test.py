"""
# Incremental CSV Database Backup from NCI to S3

This DAG runs daily at 1am Canberra Time.

It dumps any changes to the ODC Database into a CSV file per table, and uploads them to

    s3://nci-db-dump/csv-test/${datestring}/

This DAG should be idempotent, ie. running repeatedly is safe.
"""
from textwrap import dedent

from airflow import DAG
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.ssh_operator import SSHOperator

from datetime import datetime, timedelta

import pendulum

local_tz = pendulum.timezone("Australia/Canberra")

default_args = {
    "owner": "nikita",
    "depends_on_past": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2020, 9, 10, 1, tzinfo=local_tz),
    "timeout": 60 * 60 * 2,  # For running SSH Commands
    "ssh_conn_id": "lpgs_gadi",
    "remote_host": "gadi-dm.nci.org.au",
    "email_on_failure": True,
    "email": "nikita.gandhi@ga.gov.au",
}

with DAG(
    "nci_incremental_csv_db_backup_test",
    default_args=default_args,
    catchup=False,
    schedule_interval="@daily",
    max_active_runs=1,
    tags=["nci"],
) as dag:

    COMMON = dedent(
        """
        set -e
        # Load dea module to ensure that pg_dump version and the server version matches
        module use /g/data/v10/public/modules/modulefiles
        module load dea

        host=dea-db.nci.org.au
        datestring={{ ds_nodash }}
        datestring_psql={{ ds }}
        file_prefix="${host}-${datestring}"


        output_dir=$TMPDIR/pg_change_csvs_${datestring}
        mkdir -p ${output_dir}
        cd ${output_dir}

    """
    )

    # Each ODC table has different date columns available for determining if changes have been made.
    # This requires a custom query for each.
    # Each of the 5 tables are dumped into separate CSV files.
    run_changes_csv_dump = SSHOperator(
        task_id="dump_table_changes_to_csv",
        command=COMMON
        + dedent(
            """
            set -euo pipefail
            IFS=$'\n\t'

            for table in agdc.dataset_type agdc.metadata_type; do
                echo Dumping changes from $table
                psql --quiet -c "\\copy (select * from $table where updated <@ tstzrange('{{ prev_ds }}', '{{ ds }}') or added <@ tstzrange('{{ prev_ds }}', '{{ ds }}')) to stdout with (format csv)" -h ${host} -d datacube | grep -v "^Time:" | gzip -c - > ${table}_changes.csv.gz
            done

            table=agdc.dataset
            echo Dumping changes from $table
            psql --quiet -c "\\copy (select * from $table where updated <@ tstzrange('{{ prev_ds }}', '{{ ds }}') or archived <@ tstzrange('{{ prev_ds }}', '{{ ds }}') or added <@ tstzrange('{{ prev_ds }}', '{{ ds }}')) to stdout with (format csv)" -h ${host} -d datacube | grep -v "^Time:" | gzip -c - > ${table}_changes.csv.gz

            table=agdc.dataset_location
            echo Dumping changes from $table
            psql --quiet -c "\\copy (select * from $table where added <@ tstzrange('{{ prev_ds }}', '{{ ds }}') or archived <@ tstzrange('{{ prev_ds }}', '{{ ds }}')) to stdout with (format csv)" -h ${host} -d datacube | grep -v "^Time:"| gzip -c - > agdc.dataset_location_changes.csv.gz

            table=agdc.dataset_source
            echo Dumping changes from $table
            psql --quiet -c "\\copy (select * from $table where dataset_ref in (select id  from agdc.dataset where added <@ tstzrange('{{ prev_ds }}', '{{ ds }}'))) to stdout with (format csv)" -h ${host} -d datacube | grep -v "^Time:" | gzip -c - > agdc.dataset_source_changes.csv.gz

        """
        ),
    )

    # Grab credentials from an Airflow Connection
    aws_conn = AwsHook(aws_conn_id="aws_nci_db_backup")

    upload_change_csvs_to_s3 = SSHOperator(
        task_id="upload_change_csvs_to_s3",
        params={"aws_conn": aws_conn.get_credentials()},
        command=COMMON
        + dedent(
            """
            export AWS_ACCESS_KEY_ID={{params.aws_conn.access_key}}
            export AWS_SECRET_ACCESS_KEY={{params.aws_conn.secret_key}}

            aws s3 sync ./ s3://nci-db-dump/csv-test/${datestring}/ --content-encoding gzip --no-progress

            # Upload md5sums last, as a marker that it's complete.
            md5sum * > md5sums
            cat md5sums
            aws s3 cp md5sums s3://nci-db-dump/csv-test/${datestring}/

            # Remove the CSV directory
            cd ..
            rm -rf ${output_dir}

        """
        ),
    )

    run_changes_csv_dump >> upload_change_csvs_to_s3