"""
# Produce and Index Fractional Cover on the NCI

**Upstream dependency:**
[Ingestion](/tree?dag_id=nci_dataset_ingest)

**Downstream dependency:**
[COG and Upload](/tree?dag_id=nci_cog_and_upload)
"""
from textwrap import dedent

from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor
from nci_collection_2.nci_common import c2_schedule_interval, c2_default_args, DAYS
from operators.ssh_operators import ShortCircuitSSHOperator
from sensors.pbs_job_complete_sensor import PBSJobSensor

FC_PRODUCTS = [
    "ls7_fc_albers",
    "ls8_fc_albers",
]

dag = DAG(
    "nci_fractional_cover",
    doc_md=__doc__,
    default_args=c2_default_args,
    catchup=False,
    schedule_interval=c2_schedule_interval,
    tags=["nci", "landsat_c2"],
    default_view="tree",
)

with dag:
    COMMON = dedent(
        """
        {% set work_dir = '/g/data/v10/work/' + params.product + '/' + ts_nodash %}

        module use /g/data/v10/public/modules/modulefiles;
        module load {{ params.module }};

        """
    )

    for product in FC_PRODUCTS:
        ing_product = product.replace("fc", "nbart")
        ingest_completed = ExternalTaskSensor(
            task_id=f"ingest_completed_{ing_product}",
            external_dag_id="nci_dataset_ingest",
            external_task_id=f"wait_for_{ing_product}_ingest",
            mode="reschedule",
            timeout=1 * DAYS,
        )
        generate_tasks = SSHOperator(
            command=COMMON
            + dedent(
                """
                APP_CONFIG="$(datacube-fc list | grep "{{ params.product }}")";

                mkdir -p {{ work_dir }}
                cd {{work_dir}}
                datacube --version
                datacube-fc --version
                datacube-fc generate -vv --app-config=${APP_CONFIG} --output-filename tasks.pickle
            """
            ),
            params={"product": product},
            task_id=f"generate_tasks_{product}",
            timeout=60 * 20,
        )
        test_tasks = ShortCircuitSSHOperator(
            command=COMMON
            + dedent(
                """
                cd {{work_dir}}
                datacube-fc run -vv --dry-run --input-filename {{work_dir}}/tasks.pickle
            """
            ),
            params={"product": product},
            task_id=f"test_tasks_{product}",
            timeout=60 * 20,
        )

        submit_task_id = f"submit_{product}"
        submit_fc_job = SSHOperator(
            task_id=submit_task_id,
            command=COMMON
            + dedent(
                """
              # TODO Should probably use an intermediate task here to calculate job size
              # based on number of tasks.
              # Although, if we run regularaly, it should be pretty consistent.
              # Last time I checked, FC took about 30s per tile (task).

              cd {{work_dir}}

              qsub -N {{ params.product}} \
              -q {{ params.queue }} \
              -W umask=33 \
              -l wd,walltime=5:00:00,mem=190GB,ncpus=48 -m abe \
              -l storage=gdata/v10+gdata/fk4+gdata/rs0+gdata/if87 \
              -M nci.monitor@dea.ga.gov.au \
              -P {{ params.project }} -o {{ work_dir }} -e {{ work_dir }} \
              -- /bin/bash -l -c \
                  "module use /g/data/v10/public/modules/modulefiles/; \
                  module load {{ params.module }}; \
                  datacube-fc run -vv --input-filename {{work_dir}}/tasks.pickle --celery pbs-launch"
            """
            ),
            params={"product": product},
            timeout=60 * 20,
            do_xcom_push=True,
        )

        wait_for_completion = PBSJobSensor(
            task_id=f"wait_for_{product}",
            pbs_job_id="{{ ti.xcom_pull(task_ids='%s') }}" % submit_task_id,
            timeout=60 * 60 * 24 * 7,
        )

        ingest_completed >> generate_tasks >> test_tasks >> submit_fc_job >> wait_for_completion
