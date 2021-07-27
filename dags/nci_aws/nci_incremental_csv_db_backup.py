"""# Incremental CSV Database Backup from NCI to S3

This DAG runs daily soon after midnight Canberra Time.

It dumps any changes in the NCI ODC Database into CSV files, one per table, and
uploads them to:

    s3://nci-db-dump/csv-changes/<YYYY-MM-DD>/

This DAG should be idempotent, ie. running repeatedly is safe.


**Downstream dependency:**
[K8s NCI DB Incremental Sync](/tree?dag_id=k8s_nci_db_incremental_sync)

"""
from textwrap import dedent

from airflow import DAG
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook as AwsHook
from airflow.providers.ssh.operators.ssh import SSHOperator

from datetime import datetime, timedelta

import pendulum

from nci_collection_2.nci_common import HOURS

local_tz = pendulum.timezone("Australia/Canberra")

default_args = {
    "owner": "Damien Ayers",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2020, 11, 15, tzinfo=local_tz),
    "timeout": 2 * HOURS,  # For running SSH Commands
    "ssh_conn_id": "lpgs_gadi",
    "remote_host": "gadi-dm.nci.org.au",
    "email_on_failure": True,
    "email_on_retry": False,
    "email": "damien.ayers@ga.gov.au",
}

with DAG(
    "nci_incremental_csv_db_backup",
    default_args=default_args,
    catchup=True,
    schedule_interval="@daily",
    tags=["nci", "explorer"],
) as dag:

    # Language="Shell Script"
    COMMON = dedent(
        """
        set -e
        # Load dea module to ensure that pg_dump version and the server version matches
        module use /g/data/v10/public/modules/modulefiles
        module load dea

        host=dea-db.nci.org.au
        datestring={{ execution_date.in_tz("Australia/Canberra").to_date_string() }}
        file_prefix="${host}-${datestring}"


        output_dir=/scratch/v10/lpgs/pg_change_csvs_${datestring}
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
            export PGDATABASE=datacube
            export PGHOST=${host}

            for table in agdc.dataset_type agdc.metadata_type; do
                echo Dumping changes from $table
                psql --no-psqlrc --quiet --csv -c "select * from $table where updated <@ tstzrange('{{ execution_date.isoformat() }}', '{{next_execution_date.isoformat()}}') or added <@ tstzrange('{{ execution_date.isoformat() }}', '{{next_execution_date.isoformat()}}')" | gzip > ${table}_changes.csv.gz
            done

            table=agdc.dataset
            echo Dumping changes from $table
            psql --no-psqlrc --quiet --csv -c "select * from $table where updated <@ tstzrange('{{ execution_date.isoformat() }}', '{{next_execution_date.isoformat()}}') or archived <@ tstzrange('{{ execution_date.isoformat() }}', '{{next_execution_date.isoformat()}}') or added <@ tstzrange('{{ execution_date.isoformat() }}', '{{next_execution_date.isoformat()}}');" | gzip > ${table}_changes.csv.gz

            table=agdc.dataset_location
            echo Dumping changes from $table
            psql --no-psqlrc --quiet --csv -c "select * from $table where added <@ tstzrange('{{ execution_date.isoformat() }}', '{{next_execution_date.isoformat()}}') or archived <@ tstzrange('{{ execution_date.isoformat() }}', '{{next_execution_date.isoformat()}}');" | gzip > agdc.dataset_location_changes.csv.gz

            table=agdc.dataset_source
            echo Dumping changes from $table
            psql --no-psqlrc --quiet --csv -c "select * from $table where dataset_ref in (select id  from agdc.dataset where added <@ tstzrange('{{ execution_date.isoformat() }}', '{{next_execution_date.isoformat()}}'));" | gzip > agdc.dataset_source_changes.csv.gz

        """
        ),
    )

    # Grab credentials from an Airflow Connection
    aws_conn = AwsHook(aws_conn_id="aws_nci_db_backup", client_type="s3")

    upload_change_csvs_to_s3 = SSHOperator(
        task_id="upload_change_csvs_to_s3",
        params={"aws_conn": aws_conn},
        command=COMMON
        + dedent(
            # Language="Shell Script"
            """
            {% set creds = params.aws_conn.get_credentials() %}
            export AWS_ACCESS_KEY_ID={{creds.access_key}}
            export AWS_SECRET_ACCESS_KEY={{creds.secret_key}}

            aws s3 sync ./ s3://nci-db-dump/csv-changes/${datestring}/ --content-encoding gzip --no-progress

            # Upload md5sums last, as a marker that it's complete.
            md5sum * > md5sums
            cat md5sums
            aws s3 cp md5sums s3://nci-db-dump/csv-changes/${datestring}/

            # Remove the CSV directory
            cd ..
            rm -rf ${output_dir}

        """
        ),
    )

    run_changes_csv_dump >> upload_change_csvs_to_s3
