"""
# Collection 3 NCI to AWS Automation Backlog

This DAG runs tasks on Gadi at the NCI. User check metadata files in S3, and create
the incorrect meatadata file list. Then this one-off DAG sync incorrect Collection 3
data from NCI to AWS S3 bucket again.

This https://gajira.atlassian.net/browse/DEADM-1619 fix the missing data bug. The
current DAG aims to upload the missing files. Before run this DAG, the
https://gist.github.com/omad/6ba87227b57f842b05fe9ffad81ecbf3 creates missing file
list. It:

 * Uploads `incorrect_metadata_in_s3.csv` from script folder to NCI work folder
 * Uploads `C3 to S3 rolling` script to NCI work folder.
 * Executes uploaded rolling script to upload `Collection 3` data to AWS `S3` bucket.

This DAG takes following input parameters from `nci_c3_upload_s3_config` variable:

 * `s3bucket`: Name of the S3 bucket. `"dea-public-data"`
 * `s3path`: Path prefix of the S3. `"baseline"`
 * `s3baseurl`: Base URL of the S3. `"s3://dea-public-data"`
 * `explorerbaseurl`: Base URL of the explorer. `"https://explorer.dea.ga.gov.au"`
 * `snstopic`: ARN of the SNS topic. `"arn:aws:sns:ap-southeast-2:538673716275:dea-public-data-landsat-3"`

Note: this DAG aims to fix gap between NCI and S3. So always run with `"--force-update"` to do a fresh sync.

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

local_tz = pendulum.timezone("Australia/Canberra")

# language="Shell Script"
RUN_UPLOAD_SCRIPT = dedent(
    """
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
            --filepath '{{ work_dir }}/incorrect_metadata_in_s3.csv' \
            --ncidir '{{ params.nci_dir }}' \
            --s3path '{{ var.json.nci_c3_upload_s3_config.s3path }}' \
            --s3bucket '{{ var.json.nci_c3_upload_s3_config.s3bucket }}' \
            --s3baseurl '{{ var.json.nci_c3_upload_s3_config.s3baseurl }}' \
            --explorerbaseurl '{{ var.json.nci_c3_upload_s3_config.explorerbaseurl }}' \
            --snstopic '{{ var.json.nci_c3_upload_s3_config.snstopic }}' \
            --force-update
"""
)


default_args = {
    "owner": "Sai Ma",
    "start_date": datetime(2020, 9, 25, tzinfo=local_tz),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "timeout": 1200,  # For running SSH Commands
    "email_on_failure": False,
    "email_on_retry": False,
    "email": "sai.ma@ga.gov.au",
    "ssh_conn_id": "lpgs_gadi",
    "aws_conn_id": "dea_public_data_landsat_3_sync",
}

dag = DAG(
    "nci_c3_upload_s3_backlog",
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval=None,  # manually trigger it
    tags=["nci", "landsat_c3_backlog"],
)

with dag:

    WORK_DIR = f'/g/data/v10/work/c3_upload_s3/{"{{ ts_nodash }}"}'
    COMMON = dedent(
        """
            {% set work_dir = '/g/data/v10/work/c3_upload_s3_backlog/' + ts_nodash -%}
            """
    )

    # Uploading CSV file to NCI
    sftp_missing_csv = SFTPOperator(
        task_id="sftp_incorrect_metadata_in_s3_csv",
        local_filepath=str(
            Path(conf.get("core", "dags_folder")).parent
            / "scripts/incorrect_metadata_in_s3.csv"
        ),
        remote_filepath=f"{WORK_DIR}/incorrect_metadata_in_s3.csv",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True,
    )

    # Uploading c3_to_s3_rolling.py script to NCI
    sftp_c3_to_s3_script = SFTPOperator(
        task_id="sftp_c3_to_s3_script",
        local_filepath=str(
            Path(conf.get("core", "dags_folder")).parent / "scripts/c3_to_s3_rolling.py"
        ),
        remote_filepath=f"{WORK_DIR}/c3_to_s3_rolling.py",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True,
    )
    # Execute script to upload Landsat collection 3 data to s3 bucket
    aws_hook = AwsHook(aws_conn_id=dag.default_args["aws_conn_id"], client_type="s3")
    execute_c3_to_s3_script = SSHOperator(
        task_id="execute_c3_to_s3_script",
        command=COMMON + RUN_UPLOAD_SCRIPT,
        remote_host="gadi-dm.nci.org.au",
        params={
            "aws_hook": aws_hook,
            "nci_dir": "/g/data/xu18/ga/",
        },
    )

    # Deletes working folder and uploaded script file
    clean_nci_work_dir = SSHOperator(
        task_id="clean_nci_work_dir",
        # Remove work dir after aws s3 sync
        command=COMMON
        + dedent(
            """
                set -eux
                rm -vrf "{{ work_dir }}"
            """
        ),
    )

    sftp_missing_csv >> sftp_c3_to_s3_script
    sftp_c3_to_s3_script >> execute_c3_to_s3_script
    execute_c3_to_s3_script >> clean_nci_work_dir
