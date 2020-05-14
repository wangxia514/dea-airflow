"""
# Sentinel-2 data routine upload to S3 bucket

This DAG runs tasks on Gadi at the NCI. This DAG routinely sync Sentinel-2 data to S3 bucket. It:

 * Create necessary working folder at NCI
 * Uploads Sentinel-2 to S3 rolling script to NCI work folder
 * Executes uploaded rolling script to upload Sentinel-2 data to S3 bucket

This DAG takes following input parameters:

 * s3bucket: Name of the S3 bucket (e.g. 'dea-public-data-dev')
 * numdays: Number of days to process before the end date (e.g. '1')
 * enddate: End date for processing (e.g. '2020-02-21')
 * doupdate: Check to update granules if already exist. Set 'yes' to update else 'no' or don't set (e.g. 'no')

"""

from datetime import datetime,timedelta
from textwrap import dedent
import os

from airflow import DAG, AirflowException
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.contrib.operators.sftp_operator import SFTPOperator
from airflow.contrib.operators.sftp_operator import SFTPOperation


default_args = {
    'owner': 'Sachit Rajbhandari',
    'start_date': datetime(2020, 5, 8),
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    'ssh_conn_id': 'lpgs_gadi',
    'email_on_failure': False,
    'email': 'sachit.rajbhandari@ga.gov.au',
    'params': {
        's3bucket': 'dea-public-data-dev',
        'numdays': '1',
        'enddate': '2020-02-21',
        'doupdate': 'no',
    }
}

dag = DAG(
    'nci_s2_upload_s3',
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    template_searchpath='templates/',
    max_active_runs=1,
    default_view='graph',
    tags=['nci', 'sentinel_2'],
    params={'workdir': '/g/data/v10/work/s2_nbar_rolling_archive/ts_nodash_' + default_args['params']['enddate'] + '_' + default_args['params']['numdays']}
)


with dag:
    # Creating working directory /g/data/v10/work/s2_nbar_rolling_archive/ts_nodash_<end_date>_<num_days>
    create_nci_work_dir = SSHOperator(
        task_id='create_nci_work_dir',
        command=dedent('''
            set -eux
            {% set work_dir = params.workdir -%}
            mkdir -p {{work_dir}}
        '''),
    )
    # Uploading s2_to_s3_rolling.py script to NCI
    sftp_s2_to_s3_rolling_script = SFTPOperator(
        task_id='sftp_s2_to_s3_rolling_script',
        local_filepath=os.path.abspath('./scripts/s2_to_s3_rolling.py'),
        remote_filepath=dag.params['workdir']+'/s2_to_s3_rolling.py',
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True,
    )
    # Excecute script to upload sentinel-2 data to s3 bucket
    aws_conn = AwsHook(aws_conn_id='dea_public_data_upload')
    execute_s2_to_s3_rolling_script = SSHOperator(
        task_id='execute_s2_to_s3_rolling_script',
        command=dedent("""
            cd {{params.workdir}}

            qsub -N s2nbar-rolling-archive -o "{{params.workdir}}" -e "{{params.workdir}}" <<EOF
            #!/usr/bin/env bash

            # Set up PBS job variables
            #PBS -P v10
            #PBS -q copyq

            #PBS -l wd

            ## Resource limits
            #PBS -l mem=1GB
            #PBS -l ncpus=1
            #PBS -l walltime=10:00:00

            ## The requested job scratch space.
            #PBS -l jobfs=1GB
            #PBS -l storage=gdata/if87+gdata/v10
            #PBS -m abe -M nci.monitor@dea.ga.gov.au

            # echo on and exit on fail
            set -ex

            # Set up our environment
            # shellcheck source=/dev/null
            source "$HOME"/.bashrc

            # Load the latest stable DEA module
            module use /g/data/v10/public/modules/modulefiles
            module load dea
            
            export AWS_ACCESS_KEY_ID={{params.aws_conn.access_key}}
            export AWS_SECRET_ACCESS_KEY={{params.aws_conn.secret_key}}

            python3 '{{ params.workdir }}/s2_to_s3_rolling.py' '{{ params.numdays }}' '{{ params.s3bucket }}' '{{ params.enddate }}' '{{ params.doupdate }}'

            EOF
        """),
        params={'aws_conn': aws_conn.get_credentials()},
    )
    create_nci_work_dir >> sftp_s2_to_s3_rolling_script >> execute_s2_to_s3_rolling_script
