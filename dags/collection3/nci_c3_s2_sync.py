"""
# Sentinel 2 Collection 3 - NCI to AWS Upload Automation
This DAG runs tasks on Gadi at the NCI. This DAG routinely syncs Collection 3
data from NCI to AWS S3 bucket. It:
 * Lists scenes to be uploaded to the S3 bucket, based on what is indexed in the NCI Database.
 * Uploads the `NCI C3 S2 Upload AWS` and 'NCI C3 S2 Data Verification' scripts to a temporary NCI work folder.
 * Executes the previously uploaded script, which performs the upload to S3 process.
"""
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent

import pendulum
from airflow import DAG
from airflow.configuration import conf
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook as AwsHook
from airflow.providers.sftp.operators.sftp import SFTPOperator, SFTPOperation
from airflow.providers.ssh.operators.ssh import SSHOperator
from infra.connections import AWS_WAGL_NRT_CONN

HOURS = 60 * 60
MINUTES = 60
DAYS = HOURS * 24
WORK_DIR = "/g/data/v10/work/s2_c3_aws_sync"

local_tz = pendulum.timezone("Australia/Canberra")

# language="Shell Script"
COMMON = dedent(
    """
        {% set work_dir = '/g/data/v10/work/s2_c3_aws_sync/' -%}
        mkdir -p {{work_dir}}
        cd {{ work_dir }}
        # echo on and exit on fail
        set -eu
        # Load the latest stable DEA module
        module use /g/data/v10/public/modules/modulefiles
        module load dea/20210527
        # Be verbose and echo what we run
        set -x
"""
)

default_args = {
    "owner": "James Miller",
    "start_date": datetime(
        2022, 11, 8, tzinfo=local_tz
    ),  # earliest date in nci DB is 2016-06-29
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email_on_retry": False,
    "email": ["james.miller@ga.gov.au"],
    "ssh_conn_id": "lpgs_gadi",
    "aws_conn_id": AWS_WAGL_NRT_CONN,
}

dag = DAG(
    "nci_c3_s3_sync",
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval="@daily",
    max_active_runs=1,
    default_view="tree",
    tags=["nci", "sentinel_2"],
)

with dag:
    # Uploading supporting scripts to NCI
    upload_uploader_script = SFTPOperator(
        task_id="upload_uploader_script",
        local_filepath=str(
            Path(conf.get("core", "dags_folder")).parent / "scripts/nci_c3_s2_upload_aws.py"
        ),
        remote_filepath=WORK_DIR + "/nci_c3_s2_upload_aws.py",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True,
    )

    upload_data_verification = SFTPOperator(
        task_id="upload_data_verification",
        local_filepath=str(
            Path(conf.get("core", "dags_folder")).parent / "scripts/nci_c3_s2_data_verification_aws.py"
        ),
        remote_filepath=WORK_DIR + "/nci_c3_s2_data_verification_aws.py",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True,
    )

    # postgres query to get data on what has changed from NCI ODC
    # language="Shell Script"
    generate_list_of_s2_to_upload = SSHOperator(
        task_id="generate_list_of_s2_to_upload",
        # language="Shell Script"
        command=COMMON
        + dedent(
            """
            rm -f granule_ids.txt
            rm -f commands.txt
            rm -f data_check.txt
            for product_name in ga_s2am_ard_3 ga_s2bm_ard_3; do
                echo Searching for $product_name datasets.
            psql --variable=ON_ERROR_STOP=1 --csv --quiet --tuples-only --no-psqlrc \
                 -h dea-db.nci.org.au datacube <<EOF >> granule_ids.txt
            SELECT dsl.uri_body, ds.archived, ds.added, ds.metadata
                FROM agdc.dataset ds
                INNER JOIN agdc.dataset_type dst ON ds.dataset_type_ref = dst.id
                INNER JOIN agdc.dataset_location dsl ON ds.id = dsl.dataset_ref
                WHERE dst.name='$product_name'
                  AND ((ds.added BETWEEN '{{ prev_execution_date }}' AND '{{ execution_date }}')
                  OR (ds.archived BETWEEN '{{ prev_execution_date }}' AND '{{ execution_date }}'));
            EOF
            done
            echo -n Num Datasets to upload:
            wc -l granule_ids.txt

        """
        ),
        remote_host="gadi-dm.nci.org.au",
        timeout=20 * MINUTES,
    )

    # Execute script to upload sentinel-2 data to s3 bucket
    aws_hook = AwsHook(aws_conn_id=dag.default_args["aws_conn_id"], client_type="s3")

    # generate the required outputs before syncing, granule_id.txt is list of granules, commands.txt is the s5cmd
    # commands to execute and data_check.txt are the individual files to verify have been successfully synced
    generate_commands = SSHOperator(
        task_id="generate_commands",
        # language="Shell Script"
        command=dedent(
            COMMON
            + """
            python3 '{{ work_dir }}/nci_c3_s2_upload_aws.py' \
            --granule_id '{{ work_dir }}/granule_ids.txt' \
            --commands_path '{{ work_dir }}/commands.txt' \
            --data_check_path '{{ work_dir }}/data_check.txt'"""
        ),
        remote_host="gadi-dm.nci.org.au",
        params={"aws_hook": aws_hook},
        timeout=20 * MINUTES,
    )

    [upload_uploader_script, upload_data_verification, generate_list_of_s2_to_upload] >> generate_commands
