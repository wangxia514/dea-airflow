"""
# Produce WOfS on the NCI via PBS
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.dummy_operator import DummyOperator

from sensors.pbs_job_complete_sensor import PBSJobSensor

default_args = {
    'owner': 'Damien Ayers',
    'start_date': datetime(2020, 3, 12),
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    'ssh_conn_id': 'lpgs_gadi',
    'params': {
        'project': 'v10',
        'queue': 'normal',
        'module': 'dea/20200603',
        'year': '2020'
    }
}

dag = DAG(
    'nci_wofs',
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    default_view='graph',
    tags=['nci', 'landsat_c2'],
)

with dag:
    start = DummyOperator(task_id='start')

    COMMON = """
          {% set work_dir = '/g/data/v10/work/wofs_albers/' + ts_nodash %}
          set -eux
          module use /g/data/v10/public/modules/modulefiles;
          module load {{ params.module }};

          APP_CONFIG=/g/data/v10/public/modules/{{params.module}}/wofs/config/wofs_albers.yaml
    """
    generate_wofs_tasks = SSHOperator(
        task_id='generate_wofs_tasks',
        command=COMMON + """

            mkdir -p {{work_dir}}
            cd {{work_dir}}
            datacube --version
            datacube-wofs --version
            datacube-wofs generate -vv --app-config=${APP_CONFIG} --year {{params.year}} --output-filename tasks.pickle
        """,
        timeout=60 * 60 * 2,
    )

    test_wofs_tasks = SSHOperator(
        task_id='test_wofs_tasks',
        command=COMMON + """
            cd {{work_dir}}
            datacube-wofs run -vv --dry-run --input-filename tasks.pickle
        """,
        timeout=60 * 20,
    )
    submit_task_id = 'submit_wofs_albers'
    submit_wofs_job = SSHOperator(
        task_id=submit_task_id,
        command=COMMON + """
          # TODO Should probably use an intermediate task here to calculate job size
          # based on number of tasks.
          # Although, if we run regularaly, it should be pretty consistent.
          # Last time I checked, FC took about 30s per tile (task).

          cd {{work_dir}}

          qsub -N wofs_albers \
          -q {{ params.queue }} \
          -W umask=33 \
          -l wd,walltime=5:00:00,mem=190GB,ncpus=48 -m abe \
          -l storage=gdata/v10+gdata/fk4+gdata/rs0+gdata/if87 \
          -M nci.monitor@dea.ga.gov.au \
          -P {{ params.project }} -o {{ work_dir }} -e {{ work_dir }} \
          -- /bin/bash -l -c \
              "module use /g/data/v10/public/modules/modulefiles/; \
              module load {{ params.module }}; \
              datacube-wofs run -v --input-filename {{work_dir}}/tasks.pickle --celery pbs-launch"
        """,
        do_xcom_push=True,
        timeout=60 * 20,
    )
    wait_for_wofs_albers = PBSJobSensor(
        task_id='wait_for_wofs_albers',
        pbs_job_id="{{ ti.xcom_pull(task_ids='%s') }}" % submit_task_id,
        timeout=60 * 60 * 24 * 7,
    )
    check_for_errors = SSHOperator(
        task_id='check_for_errors',
        command=COMMON + """
        error_dir={{ ti.xcom_pull(task_ids='wait_for_wofs_albers')['Error_Path'] }}
        echo error_dir: $error_dir

        # Invert the return value of grep, we want to fail IF something matches
        echo Checking for any errors or failures in PBS output
        ! grep -i 'Task failed' $error_dir/*.ER

        # I would like to match on 'ERROR' too, but there are spurious redis related errors

        """,
        timeout=60 * 20,
    )

    start >> generate_wofs_tasks >> test_wofs_tasks >> submit_wofs_job >> wait_for_wofs_albers
    wait_for_wofs_albers >> check_for_errors
