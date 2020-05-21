"""
# Sentinel-2 data routine upload to S3 bucket

This DAG runs tasks on Gadi at the NCI. This DAG routinely sync Sentinel-2
data to S3 bucket. It:

 * Create necessary working folder at NCI
 * Uploads Sentinel-2 to S3 rolling script to NCI work folder
 * Executes uploaded rolling script to upload Sentinel-2 data to S3 bucket

This DAG takes following input parameters from "nci_s2_upload_s3_config" variable:

 * start_date: Start date for DAG run (e.g. '2020-5-8')
 * end_date: End date for DAG run (e.g. '2020-5-8')
 * catchup: Set to "True" for back fill else "False"
 * schedule_interval: Set "" for no schedule (e.g '@daily'),
 * ssh_conn_id: Provide SSH Connection ID (e.g. "lpgs_gadi")
 * aws_conn_id: Provid AWS Conection ID (e.g. "dea_public_data_dev_upload")
 * s3bucket: Name of the S3 bucket (e.g. 'dea-public-data-dev')
 * numdays: Number of days to process before the end date (e.g. '1')
 * enddate: End date for processing (e.g. '2020-02-21')
 * doupdate: Check to update granules and metadata. Select update option as below:
                'sync_granule_metadata' to update granules with metadata;
                'sync_granule' to update granules without metadata;
                'sync_metadata' to update only metadata;
                'no' or don't set to avoid update.

"""

from datetime import timedelta
from textwrap import dedent
import os

from airflow import DAG, configuration
from airflow.models import Variable
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.contrib.operators.sftp_operator import SFTPOperator, SFTPOperation

from sensors.pbs_job_complete_sensor import PBSJobSensor

dag_config = Variable.get("nci_s2_upload_s3_config", deserialize_json=True)

print(dag_config)

default_args = {
    'owner': 'Sachit Rajbhandari',
    'start_date': dag_config['start_date'] if dag_config['start_date'] else None,
    'end_date': dag_config['end_date'] if dag_config['end_date'] else None,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    'email_on_failure': False,
    'email': 'sachit.rajbhandari@ga.gov.au',
    'ssh_conn_id': dag_config['ssh_conn_id'],
    'aws_conn_id': dag_config['aws_conn_id'],
    'params': {
        's3bucket': dag_config['s3bucket'],
        'numdays': dag_config['numdays'] if dag_config['numdays'] else '0',
        'enddate': dag_config['enddate'] if dag_config['enddate'] else 'today',
        'doupdate': dag_config['doupdate'] if dag_config['doupdate'] else 'no',
    }
}


dag = DAG(
    'nci_s2_upload_s3',
    doc_md=__doc__,
    default_args=default_args,
    catchup=dag_config['catchup'] if dag_config['catchup'] == "True" else False,
    schedule_interval=dag_config['schedule_interval'] if dag_config['schedule_interval'] else None,
    template_searchpath='templates/',
    max_active_runs=1,
    default_view='graph',
    tags=['nci', 'sentinel_2'],
)


with dag:
    # Creating working directory
    # '/g/data/v10/work/s2_nbar_rolling_archive/<current_datetime>_<end_date>_<num_days>'
    COMMON = """
            {% set work_dir = '/g/data/v10/work/s2_nbar_rolling_archive/' 
            + ts_nodash + '_' + params.enddate + '_' + params.numdays  -%}
            """
    create_nci_work_dir = SSHOperator(
        task_id='create_nci_work_dir',
        command=dedent(COMMON + """
            set -eux
            mkdir -p {{work_dir}}
            echo "{{ ti.xcom_push(key="work_dir", value=work_dir) }}"
        """),
        do_xcom_push=True
    )
    # Uploading s2_to_s3_rolling.py script to NCI
    sftp_s2_to_s3_script = SFTPOperator(
        task_id='sftp_s2_to_s3_script',
        local_filepath=os.path.dirname(
            configuration.get('core', 'dags_folder')
        ) + '/scripts/s2_to_s3_rolling.py',
        remote_filepath="{{ti.xcom_pull(key='work_dir') }}/s2_to_s3_rolling.py",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True
    )
    # Excecute script to upload sentinel-2 data to s3 bucket
    aws_conn = AwsHook(aws_conn_id=dag.default_args['aws_conn_id'])
    execute_s2_to_s3_script = SSHOperator(
        task_id='execute_s2_to_s3_script',
        command=dedent(COMMON + """
            cd {{work_dir}}

            qsub -N s2nbar-rolling-archive \
            -o "{{work_dir}}" \
            -e "{{work_dir}}" <<EOF
            #!/bin/bash

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

            # Export AWS Access key/secret from Airflow connection module
            export AWS_ACCESS_KEY_ID={{params.aws_conn.access_key}}
            export AWS_SECRET_ACCESS_KEY={{params.aws_conn.secret_key}}

            python3 '{{ work_dir }}/s2_to_s3_rolling.py' \
                    'sync' \
                    '{{ params.numdays }}' \
                    '{{ params.s3bucket }}' \
                    '{{ params.enddate }}' \
                    '{{ params.doupdate }}'
                
            EOF
        """),
        params={'aws_conn': aws_conn.get_credentials()},
        timeout=60 * 5,
        do_xcom_push=True
    )
    wait_for_script_execution = PBSJobSensor(
        task_id='wait_for_script_execution',
        pbs_job_id="{{ ti.xcom_pull(task_ids='execute_s2_to_s3_script') }}",
        timeout=60 * 60 * 24 * 7,
        do_xcom_push=True
    )
    check_log = SSHOperator(
        task_id='check_log',
        command=dedent(COMMON + """
            cd {{work_dir}}
            
            # echo on and exit on fail
            set -ex
            
            # Load the latest stable DEA module
            module use /g/data/v10/public/modules/modulefiles
            module load dea
            
            python3 '{{ work_dir }}/s2_to_s3_rolling.py' \
                    'log' \
                    '{{ work_dir }}' \
                    '{{ ti.xcom_pull(key='pbs_job_id') }}' 
            
        """),
    )
    create_nci_work_dir >> sftp_s2_to_s3_script >> execute_s2_to_s3_script
    execute_s2_to_s3_script >> wait_for_script_execution >> check_log
