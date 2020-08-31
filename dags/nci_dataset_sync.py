"""
# Index (Sync) new Collection 2 ARD Datasets on the NCI
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator

from sensors.pbs_job_complete_sensor import PBSJobSensor

synced_products = [
    "ls8_nbar_scene",
    "ls8_nbart_scene",
    "ls8_pq_scene",
    "ls8_pq_legacy_scene",
    "ls7_nbar_scene",
    "ls7_nbart_scene",
    "ls7_pq_scene",
    "ls7_pq_legacy_scene",
]

SYNC_PREFIX_PATH = {
    "ls8_nbar_scene": "/g/data/rs0/scenes/nbar-scenes-tmp/ls8/",
    "ls7_nbar_scene": "/g/data/rs0/scenes/nbar-scenes-tmp/ls7/",
    "ls8_nbart_scene": "/g/data/rs0/scenes/nbar-scenes-tmp/ls8/",
    "ls7_nbart_scene": "/g/data/rs0/scenes/nbar-scenes-tmp/ls7/",
    "ls8_pq_scene": "/g/data/rs0/scenes/pq-scenes-tmp/ls8/",
    "ls7_pq_scene": "/g/data/rs0/scenes/pq-scenes-tmp/ls7/",
    "ls8_pq_legacy_scene": "/g/data/rs0/scenes/pq-legacy-scenes-tmp/ls8/",
    "ls7_pq_legacy_scene": "/g/data/rs0/scenes/pq-legacy-scenes-tmp/ls7/",
}

SYNC_SUFFIX_PATH = {
    "ls8_nbar_scene": "/??/output/nbar/",
    "ls7_nbar_scene": "/??/output/nbar/",
    "ls8_nbart_scene": "/??/output/nbart/",
    "ls7_nbart_scene": "/??/output/nbart/",
    "ls8_pq_scene": "/??/output/pqa/",
    "ls7_pq_scene": "/??/output/pqa/",
    "ls8_pq_legacy_scene": "/??/output/pqa/",
    "ls7_pq_legacy_scene": "/??/output/pqa/",
}

SYNC_COMMAND = """
  {% set work_dir = '/g/data/v10/work/sync/' + params.product + '/' + ds -%}
  {% set sync_cache_dir = work_dir + '/cache' -%}
  {% set sync_path = params.sync_prefix_path + params.year + params.sync_suffix_path -%}
  
  mkdir -p {{ sync_cache_dir }};
  qsub -N sync_{{ params.product}}_{{ params.year }} \
  -q {{ params.queue }} \
  -W umask=33 \
  -l wd,walltime=20:00:00,mem=3GB -m abe \
  -l storage=gdata/v10+gdata/fk4+gdata/rs0+gdata/if87 \
  -M nci.monitor@dea.ga.gov.au \
  -P {{ params.project }} -o {{ work_dir }} -e {{ work_dir }} \
  -- /bin/bash -l -c \
      "source $HOME/.bashrc; \
      module use /g/data/v10/public/modules/modulefiles/; \
      module load {{ params.module }}; \
      dea-sync -vvv --cache-folder {{sync_cache_dir}} -j 1 --update-locations --index-missing {{ sync_path }}"
"""

default_args = {
    "owner": "Damien Ayers",
    "depends_on_past": False,
    "start_date": datetime(2020, 3, 4),
    "email": ["damien.ayers@ga.gov.au"],
    "email_on_failure": True,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "params": {
        "project": "v10",
        "queue": "normal",
        "module": "dea/unstable",
        "year": "2020",
    },
}

with DAG(
    "nci_dataset_sync",
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    default_view="graph",
    tags=["nci", "landsat_c2"],
) as dag:
    for product in synced_products:
        submit_sync = SSHOperator(
            task_id=f"submit_sync_{product}",
            ssh_conn_id="lpgs_gadi",
            command=SYNC_COMMAND,
            params={
                "product": product,
                "sync_prefix_path": SYNC_PREFIX_PATH[product],
                "sync_suffix_path": SYNC_SUFFIX_PATH[product],
            },
            do_xcom_push=True,
            timeout=90,  # For running SSH Commands
        )

        wait_for_completion = PBSJobSensor(
            task_id=f"wait_for_{product}",
            ssh_conn_id="lpgs_gadi",
            pbs_job_id="{{ ti.xcom_pull(task_ids='submit_sync_%s') }}" % product,
        )
        submit_sync >> wait_for_completion
