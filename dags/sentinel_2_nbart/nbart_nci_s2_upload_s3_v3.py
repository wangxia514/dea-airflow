"""
# Sentinel-2 data routine sync to S3 bucket
This DAG runs tasks on Gadi at the NCI. This DAG routinely sync Sentinel-2
data from NCI to AWS S3 bucket. It:
 * Uploads `Sentinel-2 to S3 rolling` script to NCI work folder.
 * Finds all the new data added since the last run, saves them into a txt file
 * Executes the upload script to upload the data and mangle and upload the metadata file to S3
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

from infra.sns_topics import SENTINEL_2_ARD_TOPIC_ARN

HOURS = 60 * 60
MINUTES = 60
DAYS = HOURS * 24
WORK_DIR = "/g/data/v10/work/s2_nbart_rolling_archive"

local_tz = pendulum.timezone("Australia/Canberra")

# language="Shell Script"
COMMON = dedent(
    """
        {% set work_dir = '/g/data/v10/work/s2_nbart_rolling_archive/' + ds  -%}
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
    "owner": "Kieran Ricardo",
    "start_date": datetime(
        2016, 6, 1, tzinfo=local_tz
    ),  # earliest date in nci DB is 2016-06-29
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email": ["damien.ayers@ga.gov.au"],
    "ssh_conn_id": "lpgs_gadi",
    "aws_conn_id": "sentinel_2_ard_sync_user",
}

dag = DAG(
    "nbart_nci_s2_upload_s3_v3",
    doc_md=__doc__,
    default_args=default_args,
    catchup=True,
    schedule_interval="@daily",
    max_active_runs=4,
    default_view="tree",
    tags=["nci", "sentinel_2"],
)

with dag:
    # Uploading s2_to_s3_rolling.py script to NCI
    upload_uploader_script = SFTPOperator(
        task_id="upload_uploader_script",
        local_filepath=str(
            Path(conf.get("core", "dags_folder")).parent / "scripts/upload_s2_nbart.py"
        ),
        remote_filepath=WORK_DIR + "/{{ds}}/upload_s2_nbart.py",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True,
    )

    upload_utils = SFTPOperator(
        task_id="upload_utils",
        local_filepath=str(
            Path(conf.get("core", "dags_folder")).parent / "scripts/c3_to_s3_rolling.py"
        ),
        remote_filepath=WORK_DIR + "/{{ds}}/c3_to_s3_rolling.py",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True,
    )

    # language="Shell Script"
    generate_list = SSHOperator(
        task_id="generate_list_of_s2_to_upload",
        # language="Shell Script"
        command=COMMON
        + dedent(
            """

            rm -f granule_ids.txt  # In case we've been run before
            for product_name in s2a_ard_granule s2b_ard_granule; do
                echo Searching for $product_name datasets.
            psql --variable=ON_ERROR_STOP=1 --csv --quiet --tuples-only --no-psqlrc \
                 -h dea-db.nci.org.au datacube <<EOF >> granule_ids.txt
            SELECT
                    substring(ds.metadata#>>'{extent,center_dt}' for 10) || '/'
                    || replace(ds.metadata#>>'{tile_id}', 'L1C', 'ARD')
                FROM agdc.dataset ds
                INNER JOIN agdc.dataset_type dst ON ds.dataset_type_ref = dst.id
                INNER JOIN agdc.dataset_location dsl ON ds.id = dsl.dataset_ref
                WHERE dst.name='$product_name'
                  AND ds.added BETWEEN '{{ prev_execution_date }}' AND '{{ execution_date.add(days=1) }}';
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

    execute_upload = SSHOperator(
        task_id="execute_upload",
        # language="Shell Script"
        command=dedent(
            COMMON
            + """
            {% set aws_creds = params.aws_hook.get_credentials() -%}
            # Export AWS Access key/secret from Airflow connection module
            export AWS_ACCESS_KEY_ID={{aws_creds.access_key}}
            export AWS_SECRET_ACCESS_KEY={{aws_creds.secret_key}}
            python3 '{{ work_dir }}/upload_s2_nbart.py' granule_ids.txt """
            + f"{SENTINEL_2_ARD_TOPIC_ARN} \n"
        ),
        remote_host="gadi-dm.nci.org.au",
        params={"aws_hook": aws_hook},
        timeout=10 * HOURS,
    )
    [upload_uploader_script, generate_list, upload_utils] >> execute_upload
