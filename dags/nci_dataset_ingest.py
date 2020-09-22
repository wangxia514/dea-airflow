"""
# Ingest Collection 2 ARD Landsat Scenes to NetCDF

This DAG executes everything using Gadi at the NCI.

All steps except the k
"""
from textwrap import dedent
from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta

from sensors.pbs_job_complete_sensor import PBSJobSensor

INGEST_PRODUCTS = {
    'ls8_nbar_scene': 'ls8_nbar_albers',
    'ls8_nbart_scene': 'ls8_nbart_albers',
    'ls8_pq_scene': 'ls8_pq_albers',
    'ls7_nbar_scene': 'ls7_nbar_albers',
    'ls7_nbart_scene': 'ls7_nbart_albers',
    'ls7_pq_scene': 'ls7_pq_albers',
}

default_args = {
    'owner': 'Damien Ayers',
    'depends_on_past': False,
    'start_date': datetime(2020, 3, 4),
    'email': ['damien.ayers@ga.gov.au'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'params': {
        'project': 'v10',
        'queue': 'normal',
        'module': 'dea',
        'year': '2020',
        'queue_size': '10000',
    }
}

ingest_dag = DAG(
    'nci_dataset_ingest',
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    tags=['nci', 'landsat_c2'],
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

    save_tasks_command = dedent(COMMON + """
        INGESTION_CONFIG=/g/data/v10/public/modules/$(module info-loaded dea)/lib/python3.6/site-packages/digitalearthau/config/ingestion/{{ params.ing_product }}.yaml
            
        datacube -v ingest --year {{params.year}} --config-file ${INGESTION_CONFIG} --save-tasks {{task_file}}
    """)

    test_tasks_command = dedent(COMMON + """
        datacube -v ingest --allow-product-changes --load-tasks {{task_file}} --dry-run
    """)

    qsubbed_ingest_command = dedent(COMMON + """
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
    """)

    for ing_product in INGEST_PRODUCTS.values():
        save_tasks = SSHOperator(
            task_id=f'save_tasks_{ing_product}',
            ssh_conn_id='lpgs_gadi',
            command=save_tasks_command,
            params={'ing_product': ing_product},
            timeout=90,
        )
        test_tasks = SSHOperator(
            task_id=f'test_tasks_{ing_product}',
            ssh_conn_id='lpgs_gadi',
            command=test_tasks_command,
            params={'ing_product': ing_product},
            timeout=90,
        )

        submit_task_id = f'submit_ingest_{ing_product}'
        submit_ingest_job = SSHOperator(
            task_id=submit_task_id,
            ssh_conn_id='lpgs_gadi',
            command=qsubbed_ingest_command,
            params={'ing_product': ing_product},
            do_xcom_push=True,
            timeout=90,

        )
        wait_for_completion = PBSJobSensor(
            task_id=f'wait_for_{ing_product}_ingest',
            ssh_conn_id='lpgs_gadi',
            pbs_job_id="{{ ti.xcom_pull(task_ids='%s') }}" % submit_task_id
        )

        save_tasks >> test_tasks >> submit_ingest_job >> wait_for_completion
