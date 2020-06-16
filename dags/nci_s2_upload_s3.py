"""
# Sentinel-2 data routine upload to S3 bucket

This DAG runs tasks on Gadi at the NCI. This DAG routinely sync Sentinel-2
data from NCI to AWS S3 bucket. It:

 * Uploads `Sentinel-2 to S3 rolling` script to NCI work folder.
 * Executes uploaded rolling script to upload `Sentinel-2` data to AWS `S3` bucket.
 * Cleans working folder at `NCI` after upload completion.

This DAG has following configuration:

 * `start_date`: Start date for DAG run `datetime(2020, 12, 6)`.
 * `end_date`: End date for DAG run `datetime(2020, 5, 31)`.
 * `catchup`: Set to `[True]` for back fill.
 * `schedule_interval`: Set `@daily` to schedule upload daily.
 * `ssh_conn_id`: Provide SSH Connection ID `"lpgs_gadi"`.
 * `aws_conn_id`: Provide AWS Conection ID `"dea_public_data_upload"`.

This DAG takes following input parameters from `nci_s2_upload_s3_config` variable:

 * `s3bucket`: Name of the S3 bucket. `"dea-public-data"`
 * `numdays`: Number of days to process before the execution date selected is `"0"`
 * `doupdate`: Select update option as below to replace granules and metadata.
    * `'granule_metadata'` to update granules and metadata;
    * `'granule' to update'` granules without metadata;
    * `'metadata'` to update only metadata;
    * `'no'` or don't set to avoid update of existing granules/metadata..
"""
from datetime import datetime, timedelta
from textwrap import dedent
from pathlib import Path

from airflow import DAG, configuration
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.contrib.operators.sftp_operator import SFTPOperator, SFTPOperation


default_args = {
    'owner': 'Sachit Rajbhandari',
    'start_date': datetime(2020, 4, 21),
    'end_date': datetime(2020, 5, 31),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': True,
    'email': 'sachit.rajbhandari@ga.gov.au',
    'ssh_conn_id': 'lpgs_gadi',
    'aws_conn_id': 'dea_public_data_dev_upload',
}


dag = DAG(
    'nci_s2_upload_s3',
    doc_md=__doc__,
    default_args=default_args,
    catchup=True,
    schedule_interval='@daily',
    max_active_runs=4,
    default_view='graph',
    tags=['nci', 'sentinel_2'],
)


with dag:
    WORK_DIR = "/g/data/v10/work/s2_nbar_rolling_archive/{{ ds }}_{{ var.json.nci_s2_upload_s3_config.numdays }}"
    COMMON = """
            {% set work_dir = '/g/data/v10/work/s2_nbar_rolling_archive/' 
            + ds +'_' + var.json.nci_s2_upload_s3_config.numdays -%}
            """
    # Uploading s2_to_s3_rolling.py script to NCI
    sftp_s2_to_s3_script = SFTPOperator(
        task_id="sftp_s2_to_s3_script",
        local_filepath=Path(
            Path(configuration.get('core', 'dags_folder')).parent
        ).joinpath("scripts/s2_to_s3_rolling.py").as_posix(),
        remote_filepath="{}/s2_to_s3_rolling.py".format(WORK_DIR),
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True
    )
    # Execute script to upload sentinel-2 data to s3 bucket
    aws_conn = AwsHook(aws_conn_id=dag.default_args['aws_conn_id'])
    execute_s2_to_s3_script = SSHOperator(
        task_id='execute_s2_to_s3_script',
        command=dedent(COMMON + """
            cd {{ work_dir }}

            # echo on and exit on fail
            set -eux

            # Load the latest stable DEA module
            module use /g/data/v10/public/modules/modulefiles
            module load dea

            # Export AWS Access key/secret from Airflow connection module
            export AWS_ACCESS_KEY_ID={{params.aws_conn.access_key}}
            export AWS_SECRET_ACCESS_KEY={{params.aws_conn.secret_key}}

            python3 '{{ work_dir }}/s2_to_s3_rolling.py' \
                    -n '{{ var.json.nci_s2_upload_s3_config.numdays }}' \
                    -d '{{ ds }}' \
                    -b '{{ var.json.nci_s2_upload_s3_config.s3bucket }}' \
                    -u '{{ var.json.nci_s2_upload_s3_config.doupdate }}'
        """),
        remote_host='gadi-dm.nci.org.au',
        params={'aws_conn': aws_conn.get_credentials()},
        timeout=60 * 10
    )
    # Deletes working folder and uploaded script file
    clean_nci_work_dir = SSHOperator(
        task_id='clean_nci_work_dir',
        # Remove work dir after aws s3 sync
        command=dedent(COMMON + """
            set -eux
            rm -vrf "{{ work_dir }}"
        """)
    )
    sftp_s2_to_s3_script >> execute_s2_to_s3_script
    execute_s2_to_s3_script >> clean_nci_work_dir
