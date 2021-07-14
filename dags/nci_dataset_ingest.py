"""
# Ingest Collection 2 ARD Landsat Scenes to NetCDF

This DAG executes everything using Gadi at the NCI.

**Upstream dependency:**
[Dataset Sync](/tree?dag_id=nci_dataset_sync)

**Downstream dependencies:**

 * [WOfS](/tree?dag_id=nci_wofs)
 * [Fractional Cover](/tree?dag_id=nci_fractional_cover)
"""
from textwrap import dedent

from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor

from nci_common import c2_schedule_interval, c2_default_args, DAYS
from operators.ssh_operators import ShortCircuitSSHOperator
from sensors.pbs_job_complete_sensor import PBSJobSensor

INGEST_PRODUCTS = {
    "ls8_nbar_scene": "ls8_nbar_albers",
    "ls8_nbart_scene": "ls8_nbart_albers",
    "ls8_pq_scene": "ls8_pq_albers",
    "ls7_nbar_scene": "ls7_nbar_albers",
    "ls7_nbart_scene": "ls7_nbart_albers",
    "ls7_pq_scene": "ls7_pq_albers",
}

ingest_dag = DAG(
    "nci_dataset_ingest",
    doc_md=__doc__,
    default_args=c2_default_args,
    catchup=False,
    schedule_interval=c2_schedule_interval,
    tags=["nci", "landsat_c2"],
    default_view="tree",
)

with ingest_dag:
    COMMON = """
        {% set work_dir = '/g/data/v10/work/ingest/' + params.ing_product + '/' + ds -%}
        {% set task_file = 'tasks.bin' -%}

        module use /g/data/v10/public/modules/modulefiles;
        module load {{ params.module }};

        mkdir -p {{work_dir}};
        cd {{work_dir}};
    """

    save_tasks_command = COMMON + dedent(
        """
        INGESTION_CONFIG=/g/data/v10/public/modules/$(module info-loaded dea)/lib/python3.6/site-packages/digitalearthau/config/ingestion/{{ params.ing_product }}.yaml

        datacube -v ingest --year {{params.year}} --config-file ${INGESTION_CONFIG} --save-tasks {{task_file}}
    """
    )

    test_tasks_command = COMMON + dedent(
        """
        datacube -v ingest --allow-product-changes --load-tasks {{task_file}} --dry-run
    """
    )

    qsubbed_ingest_command = COMMON + dedent(
        """
        {% set distributed_script = '/home/547/lpgs/bin/run_distributed.sh' %}

        qsub \
        -N ing_{{params.ing_product}}_{{params.year}} \
        -q {{params.queue}} \
        -W umask=33 \
        -l wd,walltime=5:00:00 -m abe \
        -l ncpus=48,mem=190gb \
        -l storage=gdata/v10+gdata/fk4+gdata/rs0+gdata/if87 \
        -P {{ params.project }} -o {{ work_dir }} -e {{ work_dir }} \
        -- {{ distributed_script}} {{ params.module }} --ppn 48 \
        datacube -v ingest --allow-product-changes --load-tasks {{ task_file }} \
        --queue-size {{params.queue_size}} --executor distributed DSCHEDULER
    """
    )

    for src_product, ing_product in INGEST_PRODUCTS.items():
        wait_for_sync = ExternalTaskSensor(
            task_id=f"wait_for_sync_{src_product}",
            external_dag_id="nci_dataset_sync",
            external_task_id=f"wait_for_{src_product}",
            mode="reschedule",
            timeout=1 * DAYS,
        )
        save_tasks = SSHOperator(
            task_id=f"save_tasks_{ing_product}",
            command=save_tasks_command,
            params={"ing_product": ing_product},
            timeout=90,
        )
        test_tasks = ShortCircuitSSHOperator(
            task_id=f"test_tasks_{ing_product}",
            command=test_tasks_command,
            params={"ing_product": ing_product},
            timeout=90,
        )
        test_tasks.doc_md = dedent(
            """
                ## Instructions
                Perform some manual checks that the number of COGs to be generated seems to be about right.

                You can also do spot checks that files don't already exist in S3.

                Once you're happy, mark this job as **Success** for the DAG to continue running.
            """
        )
        submit_task_id = f"submit_ingest_{ing_product}"
        submit_ingest_job = SSHOperator(
            task_id=submit_task_id,
            command=qsubbed_ingest_command,
            params={"ing_product": ing_product},
            do_xcom_push=True,
            timeout=90,
        )
        wait_for_completion = PBSJobSensor(
            task_id=f"wait_for_{ing_product}_ingest",
            pbs_job_id="{{ ti.xcom_pull(task_ids='%s') }}" % submit_task_id,
        )

        wait_for_sync >> save_tasks >> test_tasks >> submit_ingest_job >> wait_for_completion
