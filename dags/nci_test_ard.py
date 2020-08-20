"""
# Produce Landsat C3 ARD on the NCI
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.dummy_operator import DummyOperator

from sensors.pbs_job_complete_sensor import PBSJobSensor

default_args = {
    'owner': 'Duncan Gray',
    'depends_on_past': False,  # Very important, will cause a single failure to propagate forever
    'start_date': datetime(2020, 2, 17),
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    'ssh_conn_id': 'lpgs_gadi',
    #'ssh_conn_id': 'dsg547',
    'params': {
        'project': 'v10',
        'queue': 'normal',
        'module_ass': 'ard-scene-select-py3-dea/20200814',
        'index_arg': '--index-datacube-env /g/data/v10/projects/c3_ard/dea-ard-scene-select/scripts/prod/ard_env/index-datacube.env',
        'wagl_env': '/g/data/v10/projects/c3_ard/dea-ard-scene-select/scripts/prod/ard_env/prod-wagl.env',
    }
}

# tags is in airflow >1.10.8
# My local env is airflow 1.10.10...
dag = DAG(
    'nci_test_ard',
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    default_view='graph',
    tags=['nci', 'landsat_c3'],
)

with dag:
    start = DummyOperator(task_id='start')
    completed = DummyOperator(task_id='completed')

    COMMON = """
        #  ts_nodash timestamp no dashes.
        {% set log_dir = '/home/547/dsg547/dump/airflow/' + ts_nodash + '/logdir' %}
        {% set work_dir = '/home/547/dsg547/dump/airflow/' + ts_nodash + '/workdir' %}
        {% set log_dir = '/g/data/v10/Landsat-Collection-3-ops/scene_select_test/' + ts_nodash + '/logdir' %}
        {% set work_dir = '/g/data/v10/Landsat-Collection-3-ops/scene_select_test/' + ts_nodash + '/workdir' %}
        """

    product = 'used_by_params'
    set_up = SSHOperator(
        command=COMMON + """
        # make the dir here so the output from the submit task is minimal
        mkdir -p {{ log_dir }}
        mkdir -p {{ work_dir }}
        """,
        params={},
        task_id=f'set_up',
        timeout=60 * 20,
    )

    # An example of remotely starting a qsub job (all it does is ls)
    submit_task_id = f'submit_ard_non_prod'
    submit_ard_non_prod = SSHOperator(
        task_id=submit_task_id,
        command=COMMON + """
        mkdir -p {{ log_dir }} # this is silent, this is good
        mkdir -p {{ work_dir }} # this is silent, this is good
        qsub -N ard_scene_select \
              -q  {{ params.queue }}  \
              -W umask=33 \
              -l wd,walltime=0:30:00,mem=15GB,ncpus=1 -m abe \
              -l storage=gdata/v10+scratch/v10+gdata/if87+gdata/fj7+scratch/fj7+scratch/u46+gdata/u46 \
              -P  {{ params.project }} -o {{ log_dir }} -e {{ log_dir }}  \
              -- /bin/bash -l -c \
                  "module use /g/data/v10/public/modules/modulefiles/; \
                  module use /g/data/v10/private/modules/modulefiles/; \
                  module load {{ params.module_ass }}; \
                  ard-scene-select --workdir {{ work_dir }} \
                  --pkgdir {{ work_dir }} --logdir {{ log_dir }} \
                  --env {{ params.wagl_env }}  \
                  --project {{ params.project }} \
                  --walltime 05:00:00 \
                  --run-ard"
        """,
        timeout=60 * 20,
        do_xcom_push=True,
    )
    # Note: {{ params.index_arg }}  is removed so the results are not indexed

    wait_for_completion = PBSJobSensor(
        task_id=f'wait_for_completion',
        pbs_job_id="{{ ti.xcom_pull(task_ids='%s') }}" % submit_task_id,
        timeout=60 * 60 * 24 * 7,
    )
    # A simple initial test
    ls_task = SSHOperator(command="ls",
        task_id=f'ls_task',
        timeout=60 * 20,)
    
    start >> set_up >> submit_ard_non_prod >> wait_for_completion >> completed
