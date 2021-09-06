"""
# Index (Sync) new Collection 2 ARD Datasets on the NCI


**Downstream dependency:**

 * [Ingest](/tree?dag_id=nci_dataset_ingest)
"""
from textwrap import dedent

from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.operators.dummy import DummyOperator
from nci_collection_2.nci_common import c2_default_args, c2_schedule_interval, MINUTES


SYNC_PATHS = {
    "ls8_nbar_scene": "/g/data/rs0/scenes/nbar-scenes-tmp/ls8/2021/??/output/nbar/",
    "ls7_nbar_scene": "/g/data/rs0/scenes/nbar-scenes-tmp/ls7/2021/??/output/nbar/",
    "ls8_nbart_scene": "/g/data/rs0/scenes/nbar-scenes-tmp/ls8/2021/??/output/nbart/",
    "ls7_nbart_scene": "/g/data/rs0/scenes/nbar-scenes-tmp/ls7/2021/??/output/nbart/",
    "ls8_pq_scene": "/g/data/rs0/scenes/pq-scenes-tmp/ls8/2021/??/output/pqa/",
    "ls7_pq_scene": "/g/data/rs0/scenes/pq-scenes-tmp/ls7/2021/??/output/pqa/",
    "ls8_pq_legacy_scene": "/g/data/rs0/scenes/pq-legacy-scenes-tmp/ls8/2021/??/output/pqa/",
    "ls7_pq_legacy_scene": "/g/data/rs0/scenes/pq-legacy-scenes-tmp/ls7/2021/??/output/pqa/",
}

SYNC_COMMAND = dedent(
    """
      module use /g/data/v10/public/modules/modulefiles/; \
      module load {{ params.module }}; \
      find {{ params.sync_path }} -maxdepth 1 -mindepth 1 -newermt '30 days ago' | awk '{ print $1 "/ga-metadata.yaml"}' | xargs -P 4 datacube dataset add
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
    for product, sync_path in SYNC_PATHS.items():
        submit_sync = SSHOperator(
            task_id=f"submit_sync_{product}",
            command=SYNC_COMMAND,
            params={
                "product": product,
                "sync_path": sync_path,
            },
            timeout=120 * MINUTES,  # For running SSH Commands
            remote_host="gadi-dm.nci.org.au",
        )

        # Keep this task_id around to not break the DAG history
        # Normally we would rename the DAG for a structure change, but, I don't want to
        # have to change the DAG which depends on this one by name.
        wait_for_completion = DummyOperator(task_id=f"wait_for_{product}")

        START >> submit_sync >> wait_for_completion
