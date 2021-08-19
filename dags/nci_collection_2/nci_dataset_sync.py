"""
# Index (Sync) new Collection 2 ARD Datasets on the NCI


**Downstream dependency:**

 * [Ingest](/tree?dag_id=nci_dataset_ingest)
"""
from textwrap import dedent

from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.operators.dummy import DummyOperator
from sensors.pbs_job_complete_sensor import PBSJobSensor
from nci_collection_2.nci_common import c2_default_args, c2_schedule_interval, MINUTES

SYNCED_PRODUCTS = [
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

SYNC_COMMAND = dedent(
    """
  {% set work_dir = '/g/data/v10/work/sync/' + params.product + '/' + ds -%}
  {% set sync_cache_dir = work_dir + '/cache' -%}
  {% set sync_path = params.sync_prefix_path + params.year + params.sync_suffix_path -%}

  mkdir -p {{ sync_cache_dir }};
  qsub -N sync_{{ params.product}}_{{ params.year }} \
  -q {{ params.queue }} \
  -W umask=33 \
  -l wd,walltime=9:00:00,mem=9GB -m abe \
  -l storage=gdata/v10+gdata/fk4+gdata/rs0+gdata/if87 \
  -M nci.monitor@dea.ga.gov.au \
  -P {{ params.project }} -o {{ work_dir }} -e {{ work_dir }} \
  -- /bin/bash -l -c \
      "source $HOME/.bashrc; \
      module use /g/data/v10/public/modules/modulefiles/; \
      module load {{ params.module }}; \
      dea-sync -vvv --cache-folder {{sync_cache_dir}} -j 12 --update-locations --index-missing {{ sync_path }}"
"""
)

with DAG(
    "nci_dataset_sync",
    doc_md=__doc__,
    default_args=c2_default_args,
    catchup=False,
    schedule_interval=c2_schedule_interval,
    concurrency=4,  # Limit the number of active tasks.
    tags=["nci", "landsat_c2"],
    default_view="tree",
) as dag:
    START = DummyOperator(task_id="start")
    for product in SYNCED_PRODUCTS:
        submit_sync = SSHOperator(
            task_id=f"submit_sync_{product}",
            command=SYNC_COMMAND,
            params={
                "product": product,
                "sync_prefix_path": SYNC_PREFIX_PATH[product],
                "sync_suffix_path": SYNC_SUFFIX_PATH[product],
                "queue": "copyq",
            },
            do_xcom_push=True,
            timeout=5 * MINUTES,  # For running SSH Commands
            weight_rule="upstream",  # Prefer completing downstream tasks before upstream tasks. We want to wait for
            # PBS Jobs to complete before scheduling more. They tend to timeout when running
            # too many at once.
        )

        wait_for_completion = PBSJobSensor(
            task_id=f"wait_for_{product}",
            pbs_job_id="{{ ti.xcom_pull(task_ids='submit_sync_%s') }}" % product,
            weight_rule="upstream",
        )

        START >> submit_sync >> wait_for_completion
