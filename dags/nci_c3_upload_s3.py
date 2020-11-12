"""
# Collection 3 NCI to AWS Automation

This DAG runs tasks on Gadi at the NCI. This DAG routinely sync Collection 3
data from NCI to AWS S3 bucket. It:

 * List scenes to be uploaded to S3 bucket from indexed DB.
 * Uploads `C3 to S3 rolling` script to NCI work folder.
 * Executes uploaded rolling script to upload `Collection 3` data to AWS `S3` bucket.
 * Cleans working folder at `NCI` after upload completion.

This DAG takes following input parameters from `nci_c3_upload_s3_config` variable:

 * `s3bucket`: Name of the S3 bucket. `"dea-public-data"`
 * `s3path`: Path prefix of the S3. `"baseline"`
 * `s3baseurl`: Base URL of the S3. `"s3://dea-public-data"`
 * `explorerbaseurl`: Base URL of the explorer. `"https://explorer.dea.ga.gov.au"`
 * `snstopic`: ARN of the SNS topic. `"arn:aws:sns:ap-southeast-2:538673716275:dea-public-data-landsat-3"`
 * `doupdate`: If this flag is set then do a fresh sync of data and
    replace the metadata. `"--force-update"`

"""
from datetime import datetime, timedelta
from textwrap import dedent
from pathlib import Path

from airflow import DAG, configuration
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.contrib.operators.sftp_operator import SFTPOperator, SFTPOperation

import pendulum

local_tz = pendulum.timezone("Australia/Canberra")

collection3_products = ["ga_ls5t_ard_3", "ga_ls7e_ard_3", "ga_ls8c_ard_3"]

LIST_SCENES_COMMAND = """
    mkdir -p {{ work_dir }};
    cd {{ work_dir }}
    
    echo "Execution next_date: {{ next_execution_date }} - {{ next_execution_date.timestamp() }}"
    echo "Execution date in UTC: {{ execution_date }} - {{ execution_date.timestamp() }}"
    echo "Now in UTC: `date -u`"

    # echo on and exit on fail
    set -eu

    # Load the latest stable DEA module
    module use /g/data/v10/public/modules/modulefiles
    module load dea

    # Be verbose and echo what we run
    set -x

    args="-h dea-db.nci.org.au datacube -t -A -F,"
    query="SELECT dsl.uri_body, ds.archived, ds.added, 
    to_timestamp({{ next_execution_date.timestamp() }}) at time zone 'Australia/Canberra' as exec_dt 
    FROM agdc.dataset ds 
    INNER JOIN agdc.dataset_type dst ON ds.dataset_type_ref = dst.id 
    INNER JOIN agdc.dataset_location dsl ON ds.id = dsl.dataset_ref 
    WHERE dst.name='{{ params.product }}' 
    AND (ds.added BETWEEN 
    (to_timestamp({{ execution_date.timestamp() }}) at time zone 'Australia/Canberra') 
    AND (to_timestamp({{ next_execution_date.timestamp() }}) at time zone 'Australia/Canberra') 
    OR ds.archived BETWEEN 
    (to_timestamp({{ execution_date.timestamp() }}) at time zone 'Australia/Canberra') 
    AND (to_timestamp({{ next_execution_date.timestamp() }}) at time zone 'Australia/Canberra') )
    ;"
    output_file={{ work_dir }}/{{ params.product }}.csv
    psql ${args} -c "${query}" -o ${output_file}
    cat ${output_file}
"""

RUN_UPLOAD_SCRIPT = """
    {% set aws_creds = params.aws_hook.get_credentials() -%}
    cd {{ work_dir }}

    # echo on and exit on fail
    set -eu

    # Load the latest stable DEA module
    module use /g/data/v10/public/modules/modulefiles
    module load dea

    # Be verbose and echo what we run
    set -x

    # Export AWS Access key/secret from Airflow connection module
    export AWS_ACCESS_KEY_ID={{aws_creds.access_key}}
    export AWS_SECRET_ACCESS_KEY={{aws_creds.secret_key}}

    python3 '{{ work_dir }}/c3_to_s3_rolling.py' \
            --filepath '{{ work_dir }}/{{ params.product }}.csv' \
            --ncidir '{{ params.nci_dir }}' \
            --s3path '{{ var.json.nci_c3_upload_s3_config.s3path }}' \
            --s3bucket '{{ var.json.nci_c3_upload_s3_config.s3bucket }}' \
            --s3baseurl '{{ var.json.nci_c3_upload_s3_config.s3baseurl }}' \
            --explorerbaseurl '{{ var.json.nci_c3_upload_s3_config.explorerbaseurl }}' \
            --snstopic '{{ var.json.nci_c3_upload_s3_config.snstopic }}' \
            {{ var.json.nci_c3_upload_s3_config.doupdate }}
"""

default_args = {
    "owner": "Damien Ayers",
    "start_date": datetime(2020, 9, 25, tzinfo=local_tz),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "timeout": 1200,  # For running SSH Commands
    "email_on_failure": True,
    "email": "damien.ayers@ga.gov.au",
    "ssh_conn_id": "lpgs_gadi",
    "aws_conn_id": "dea_public_data_landsat_3_sync",
}

dag = DAG(
    "nci_c3_upload_s3",
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval="0 7 * * *",
    max_active_runs=4,
    default_view="tree",
    tags=["nci", "landsat_c3"],
)

with dag:
    for product in collection3_products:
        WORK_DIR = f'/g/data/v10/work/c3_upload_s3/{product}/{"{{ ts_nodash }}"}'
        COMMON = """
                {% set work_dir = '/g/data/v10/work/c3_upload_s3/'
                + params.product  +'/' + ts_nodash -%}
                """
        # List all the scenes to be uploaded to S3 bucket
        list_scenes = SSHOperator(
            task_id=f"list_{product}_scenes",
            ssh_conn_id="lpgs_gadi",
            command=dedent(COMMON + LIST_SCENES_COMMAND),
            params={"product": product},
            do_xcom_push=False,
        )
        # Uploading c3_to_s3_rolling.py script to NCI
        sftp_c3_to_s3_script = SFTPOperator(
            task_id=f"sftp_c3_to_s3_script_{product}",
            local_filepath=Path(Path(configuration.get("core", "dags_folder")).parent)
                .joinpath("scripts/c3_to_s3_rolling.py")
                .as_posix(),
            remote_filepath="{}/c3_to_s3_rolling.py".format(WORK_DIR),
            operation=SFTPOperation.PUT,
            create_intermediate_dirs=True,
        )
        # Execute script to upload Landsat collection 3 data to s3 bucket
        aws_hook = AwsHook(aws_conn_id=dag.default_args["aws_conn_id"])
        execute_c3_to_s3_script = SSHOperator(
            task_id=f"execute_c3_to_s3_script_{product}",
            command=dedent(COMMON + RUN_UPLOAD_SCRIPT),
            remote_host="gadi-dm.nci.org.au",
            params={
                "aws_hook": aws_hook,
                "product": product,
                "nci_dir": "/g/data/xu18/ga/",
            },
        )
        # Deletes working folder and uploaded script file
        clean_nci_work_dir = SSHOperator(
            task_id=f"clean_nci_work_dir_{product}",
            # Remove work dir after aws s3 sync
            command=dedent(
                COMMON
                + """
                    set -eux
                    rm -vrf "{{ work_dir }}"
                """
            ),
            params={"product": product},
        )
        list_scenes >> sftp_c3_to_s3_script
        sftp_c3_to_s3_script >> execute_c3_to_s3_script
        execute_c3_to_s3_script >> clean_nci_work_dir
