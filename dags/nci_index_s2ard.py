"""
# Unused (was formerly for indexing S2ARD)
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator

from sensors.pbs_job_complete_sensor import PBSJobSensor

default_args = {
    'owner': 'Damien Ayers',
    'depends_on_past': False,
    'start_date': datetime(2020, 5, 1),
    'email': ['damien.ayers@ga.gov.au'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
    'params': {
        'project': 'v10',
        'module': 'dea/unstable',
        'queue': 'normal',
    }
}

SYNC_COMMAND = """
  {% set work_dir = '/g/data/v10/work/sync/' + params.product + '/' + ds -%}
  {% set sync_cache_dir = work_dir + '/cache' -%}
  {% set sync_path = '/g/data/if87/datacube/002/S2_MSI_ARD/packaged/' -%}

  mkdir -p {{ sync_cache_dir }};
  qsub -N sync_{{ params.product}} \
  -q {{ params.queue }} \
  -W umask=33 \
  -l wd,walltime=04:00:00,mem=3GB,ncpus=4 -m abe \
  -l storage=gdata/v10+gdata/rs0+gdata/if87 \
  -M nci.monitor@dea.ga.gov.au \
  -P {{ params.project }} -o {{ work_dir }} -e {{ work_dir }} \
  -- /bin/bash -l -c \
      "source $HOME/.bashrc; \
      module use /g/data/v10/public/modules/modulefiles/; \
      module load {{ params.module }}; \
      dea-sync -vvv --cache-folder {{sync_cache_dir}} -j 4 --update-locations --index-missing {{ sync_path }}"
"""

with DAG('nci_index_s2ard',
         default_args=default_args,
         catchup=False,
         # schedule_interval=timedelta(days=1),
         schedule_interval=None,
         max_active_runs=1,
         ) as dag:
    product = 's2_ard'

    submit_sync = SSHOperator(
        task_id=f'submit_sync_{product}',
        ssh_conn_id='lpgs_gadi',
        command=SYNC_COMMAND,
        params={'product': 's2_ard',},
        do_xcom_push=True,
        timeout=90,  # For submitting PBS Job
    )

    wait_for_completion = PBSJobSensor(
        task_id=f'wait_for_{product}',
        ssh_conn_id='lpgs_gadi',
        pbs_job_id="{{ ti.xcom_pull(task_ids='submit_sync_%s') }}" % product,

    )
    submit_sync >> wait_for_completion
