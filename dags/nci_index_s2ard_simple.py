from textwrap import dedent

from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator

from sensors.pbs_job_complete_sensor import PBSJobSensor

default_args = {
    'owner': 'dayers',
    'depends_on_past': False,
    'start_date': datetime(2020, 4, 1),
    'email': ['damien.ayers@ga.gov.au'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'params': {
        'project': 'v10',
        'module': 'dea/unstable',
        'queue': 'normal',
    }
}

with DAG('nci_index_s2ard',
         default_args=default_args,
         catchup=True,
         schedule_interval=timedelta(days=7),
         max_active_runs=2,
         ) as dag:

    index_datasets = SSHOperator(
        task_id=f'index_datasets',
        ssh_conn_id='lpgs_gadi',
        command=dedent('''
        set -eu
        module load dea/unstable
        
        cd /g/data/if87/datacube/002/S2_MSI_ARD/packaged

        find $(find . -maxdepth 1 -newerct '{{ prev_ds }}' ! -newerct '{{ ds }}') -name '*.yaml' -exec datacube -v dataset add --no-verify-lineage '{}' \+
        
        '''),
    )

