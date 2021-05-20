from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent

import pendulum
from airflow import DAG, configuration
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.sftp_operator import SFTPOperator, SFTPOperation
from airflow.contrib.operators.ssh_operator import SSHOperator

from infra.sns_topics import SENTINEL_2_ARD_TOPIC_ARN

HOURS = 60 * 60
MINUTES = 60
DAYS = HOURS * 24
WORK_DIR = "/g/data/v10/work/s2_nbart_rolling_archive"

local_tz = pendulum.timezone("Australia/Canberra")

# language="Shell Script"
COMMON = dedent("""
        {% set work_dir = '/g/data/v10/work/s2_nbart_rolling_archive/' + ds  -%}
        mkdir -p {{work_dir}}
        cd {{ work_dir }}
        # echo on and exit on fail
        set -eu
        # Load the latest stable DEA module
        module use /g/data/v10/public/modules/modulefiles
        module load dea
        # Be verbose and echo what we run
        set -x
""")

default_args = {
    'owner': 'Kieran Ricardo',
    'start_date': datetime(2020, 12, 1, tzinfo=local_tz), # earliest date in nci DB is 2016-06-29
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
    'email': 'kieran.ricardo@ga.gov.au',
    'ssh_conn_id': 'lpgs_gadi',
    'aws_conn_id': 'sentinel_2_ard_sync_user',
}

dag = DAG(
    'nbart_fix_metadata',
    doc_md=__doc__,
    default_args=default_args,
    catchup=True,
    schedule_interval='@daily',
    max_active_runs=4,
    default_view='tree',
    tags=['nci', 'sentinel_2'],
)

with dag:
    # Uploading s2_to_s3_rolling.py script to NCI
    upload_uploader_script = SFTPOperator(
        task_id="upload_uploader_script",
        local_filepath=str(Path(configuration.get('core', 'dags_folder')).parent / "scripts/s2_fix_metadata.py"),
        remote_filepath=WORK_DIR + "/s2_fix_metadata.py",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True
    )


    upload_utils = SFTPOperator(
        task_id="upload_utils",
        local_filepath=str(Path(configuration.get('core', 'dags_folder')).parent / "scripts/c3_to_s3_rolling.py"),
        remote_filepath=WORK_DIR + "/{{ds}}/c3_to_s3_rolling.py",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True
    )

    # Execute script to upload sentinel-2 data to s3 bucket
    aws_hook = AwsHook(aws_conn_id=dag.default_args['aws_conn_id'])
    
    execute_upload = SSHOperator(
        task_id='execute_upload',
        # language="Shell Script"
        command=dedent(COMMON + """
            {% set aws_creds = params.aws_hook.get_credentials() -%}
            # Export AWS Access key/secret from Airflow connection module
            export AWS_ACCESS_KEY_ID={{aws_creds.access_key}}
            export AWS_SECRET_ACCESS_KEY={{aws_creds.secret_key}}
            python3 '{{ work_dir }}/s2_fix_metadata.py' {{ ds }} """ + f"{SENTINEL_2_ARD_TOPIC_ARN} \n"),
        remote_host='gadi-dm.nci.org.au',
        params={'aws_hook': aws_hook},
        timeout=10 * HOURS,
    )
    [upload_uploader_script, upload_utils] >> execute_upload