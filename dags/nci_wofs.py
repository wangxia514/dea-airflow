"""
# Produce WOfS on the NCI via PBS

**Upstream dependency:**
[Ingestion](/tree?dag_id=nci_dataset_ingest)

**Downstream dependency:**
[COG and Upload](/tree?dag_id=nci_cog_and_upload)

"""
from textwrap import dedent

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor
from nci_common import c2_default_args, c2_schedule_interval
from operators.ssh_operators import ShortCircuitSSHOperator
from sensors.pbs_job_complete_sensor import PBSJobSensor

dag = DAG(
    'nci_wofs',
    doc_md=__doc__,
    default_args=c2_default_args,
    catchup=False,
    schedule_interval=c2_schedule_interval,
    tags=['nci', 'landsat_c2'],
    default_view="tree",
)
with dag:
    COMMON = dedent("""
          {% set work_dir = '/g/data/v10/work/wofs_albers/' + ts_nodash %}
          module use /g/data/v10/public/modules/modulefiles;
          module load {{ params.module }};

          set -eux
          APP_CONFIG=/g/data/v10/public/modules/$(module info-loaded dea)/wofs/config/wofs_albers.yaml
    """)

    ingest_completed = ExternalTaskSensor(
        task_id='ingest_completed',
        external_dag_id='nci_dataset_ingest',
        mode='reschedule'
    )
    generate_wofs_tasks = SSHOperator(
        task_id='generate_wofs_tasks',
        command=COMMON + dedent("""

            mkdir -p {{work_dir}}
            cd {{work_dir}}
            datacube --version
            datacube-wofs --version
            datacube-wofs generate -vv --app-config=${APP_CONFIG} --year {{params.year}} --output-filename tasks.pickle
        """),
        timeout=60 * 60 * 2,
    )

    test_wofs_tasks = ShortCircuitSSHOperator(
        task_id='test_wofs_tasks',
        command=COMMON + dedent("""
            cd {{work_dir}}
            datacube-wofs inspect-taskfile tasks.pickle
            datacube-wofs check-existing --input-filename tasks.pickle
        """),
        timeout=60 * 20,
    )
    # TODO Should probably use an intermediate task here to calculate job size
    # based on number of tasks.
    # Although, if we run regularaly, it should be pretty consistent.
    # Last time I checked, WOfS takes about 15s per tile (task).
    submit_task_id = 'submit_wofs_albers'
    submit_wofs_job = SSHOperator(
        task_id=submit_task_id,
        command=COMMON + dedent("""

          cd {{work_dir}}

          qsub -N wofs_albers \
               -q {{ params.queue }} \
               -W umask=33 \
               -l wd,walltime=5:00:00,mem=190GB,ncpus=48 \
               -m abe \
               -l storage=gdata/v10+gdata/fk4+gdata/rs0+gdata/if87 \
               -M nci.monitor@dea.ga.gov.au \
               -P {{ params.project }} \
               -o {{ work_dir }} \
               -e {{ work_dir }} \
          -- /bin/bash -l -c \
              "module use /g/data/v10/public/modules/modulefiles/; \
              module load {{ params.module }}; \
              module load openmpi; \
              mpirun datacube-wofs run-mpi -v --input-filename {{work_dir}}/tasks.pickle"
        """),
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
        command=COMMON + dedent("""
        error_dir={{ ti.xcom_pull(task_ids='wait_for_wofs_albers')['Error_Path'].split(':')[1] }}
        echo error_dir: ${error_dir}

        # Helper function to not error if the grep search term is not found
        c1grep() { grep "$@" || test $? = 1; }

        echo Checking for any errors or failures in PBS output

        task_failed_lines=$(c1grep -ci 'Task failed' ${error_dir}/*.ER)
        if [[ $task_failed_lines != "0" ]]; then
            grep -i 'Task failed' ${error_dir}/*.ER
            exit ${task_failed_lines}
        fi

        # TODO: I would like to match on 'ERROR' too, but there are spurious redis related errors
        # TODO: There's also a json-lines output file we can check.

        """),
        timeout=60 * 20,
    )

    ingest_completed >> generate_wofs_tasks >> test_wofs_tasks >> submit_wofs_job >> wait_for_wofs_albers
    wait_for_wofs_albers >> check_for_errors
