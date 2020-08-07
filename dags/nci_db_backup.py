"""
# NCI Database Backup and Upload to S3

"""
from textwrap import dedent

from airflow import DAG
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.ssh_operator import SSHOperator

from datetime import datetime, timedelta

import pendulum

local_tz = pendulum.timezone("Australia/Canberra")

default_args = {
    'owner': 'dayers',
    'depends_on_past': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2020, 5, 1, 1, tzinfo=local_tz),
    'timeout': 60*60*2,  # For running SSH Commands
    'ssh_conn_id': 'lpgs_gadi',
    'remote_host': 'gadi-dm.nci.org.au',
    'email_on_failure': True,
    'email': 'damien.ayers@ga.gov.au',
}

with DAG('nci_db_backup',
         default_args=default_args,
         catchup=False,
         schedule_interval="@daily",
         concurrency=1,
         tags=['nci'],
         ) as dag:

    COMMON = dedent('''
        set -e
        # Load dea module to ensure that pg_dump version and the server version
        # matches, when the cronjob is run from an ec2 instance
        module use /g/data/v10/public/modules/modulefiles
        module load dea/20191127

        cd /g/data/v10/agdc/backup/archive

        host=dea-db.nci.org.au
        datestring=$(date +%Y%m%d)
        file_prefix="${host}-${datestring}"
    ''')

    run_backup = SSHOperator(
        task_id='run_backup',
        command=COMMON + dedent("""
            args="-U agdc_backup -h ${host} -p 5432"

            set -x

            # Cleanup previous failures
            rm -rf "${file_prefix}"*-datacube-partial.pgdump

            # Dump
            pg_dump ${args} guest > "${file_prefix}-guest.sql"
            pg_dump ${args} datacube -n agdc -T 'agdc.dv_*' -F c -f "${file_prefix}-datacube-partial.pgdump"
            mv -v "${file_prefix}-datacube-partial.pgdump" "${file_prefix}-datacube.pgdump"

            # The globals technically contain (weakly) hashed pg user passwords, so we'll
            # tighten permissions.  (This shouldn't really matter, as users don't choose
            # their own passwords and they're long random strings, but anyway)
            umask 066
            pg_dumpall ${args} --globals-only > "${file_prefix}-globals.sql"

        """),
    )

    aws_conn = AwsHook(aws_conn_id='aws_nci_db_backup')
    upload_to_s3 = SSHOperator(
        task_id='upload_to_s3',
        params={
            'aws_conn': aws_conn.get_credentials(),
        },
        command=COMMON + dedent('''
            export AWS_ACCESS_KEY_ID={{params.aws_conn.access_key}}
            export AWS_SECRET_ACCESS_KEY={{params.aws_conn.secret_key}}
            
            s3_dump_file=s3://nci-db-dump/prod/"${file_prefix}-datacube.pgdump"
            aws s3 cp "${file_prefix}-datacube.pgdump" "${s3_dump_file}"

        ''')

    )

    run_csv_dump = SSHOperator(
        task_id='dump_tables_to_csv',
        command=COMMON + dedent("""
            set -euo pipefail
            IFS=$'\n\t'

            tables=(
                agdc.metadata_type
                agdc.dataset_type
                agdc.dataset_location
                agdc.dataset_source
                agdc.dataset
            )

            output_dir=$TMPDIR/pg_csvs_${datetime}
            mkdir -p ${output_dir}
            cd ${output_dir}

            for table in ${tables[@]}; do
                echo Dumping $table
                psql --quiet -c "\\copy $table to stdout with (format csv)" -h ${host} -d datacube | gzip -c - > $table.csv.gz

            done

        """)
    )

    upload_csvs_to_s3 = SSHOperator(
        task_id='upload_csvs_to_s3',
        params={
            'aws_conn': aws_conn.get_credentials(),
        },
        command=COMMON + dedent('''
            export AWS_ACCESS_KEY_ID={{params.aws_conn.access_key}}
            export AWS_SECRET_ACCESS_KEY={{params.aws_conn.secret_key}}


            output_dir=$TMPDIR/pg_csvs_${datetime}
            cd ${output_dir}

            aws s3 sync ./ s3://nci-db-dump/csv/${datetime}/ --content-encoding gzip --no-progress

            # Upload md5sums last, as a marker that it's complete.
            md5sum * > md5sums
            aws s3 cp md5sums s3://nci-db-dump/csv/${datetime}/

            # Remove the CSV directory
            cd ..
            rm -rf ${output_dir}

        ''')

    )

    run_backup >> upload_to_s3
    run_csv_dump >> upload_csvs_to_s3
