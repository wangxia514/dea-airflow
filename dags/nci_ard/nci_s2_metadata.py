"""
Produce ODC metadata yaml's for S2 l1 scenes and index the scenes.
Search on NCI /g/data/fj7 for the S2 l1 scenes to index.

The logs are written to NCI.

Use  params["dry_run"] == "--dry-run" to do a dry run.
For dry-run's set:
    params["ncpus"] = "1 "
    params["mem"] = "19GB"
    params["walltime"] = "00:30:00"
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.operators.dummy import DummyOperator

from sensors.pbs_job_complete_sensor import PBSJobSensor

params = {
    "project": "v10",
    "queue": "normal",
    "module": "eodatasets3/0.29.5",
    "index": "--index  ",
    "months_back": "1 ",
    "jobs_para": "1",
    "config_arg": "--config /g/data/v10/projects/c3_ard/dea-ard-scene-select/scripts/prod/ard_env/datacube.conf",
    "output_base_para": "/g/data/ka08/ga/l1c_metadata",
    "only_regions_in_para": "/g/data/v10/projects/c3_ard/dea-ard-scene-select/scene_select/data/Australian_tile_list_optimised.txt",
    "base_dir": "/g/data/v10/work/s2_c3_ard/",
    "l1_base": "/g/data/fj7/Copernicus/Sentinel-2/MSI/L1C/",
    "dry_run": "",
    "ncpus": "48 ",
    "mem": "192GB",
    "walltime": "08:00:00",
    "only-regions-in-file_para": "",
}

ssh_conn_id = "lpgs_gadi"

schedule_interval = "0 19 * * *"
# schedule_interval = None

default_args = {
    "owner": "Duncan Gray",
    "depends_on_past": False,  # Very important, will cause a single failure to propagate forever
    "start_date": datetime(2022, 11, 10),
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
    "ssh_conn_id": ssh_conn_id,
    "params": params,
}

dag = DAG(
    "nci_s2_metadata",
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval=schedule_interval,
    default_view="tree",
    tags=["nci", "s2_c3"],
)

# kick off running  eo3-prepare on NCI
with dag:
    start = DummyOperator(task_id="start")
    completed = DummyOperator(task_id="completed")

    COMMON = """
        #  ts_nodash timestamp no dashes.
        {% set log_ext = ts_nodash + '_metadata'  %}
        """

    submit_task_id = "submit_metadata_gen"
    submit_ard = SSHOperator(
        task_id=submit_task_id,
        command=COMMON
        + """
mkdir -p {{ params.base_dir }}{{ log_ext }}
a_month=$(date +%m -d ' 1  month ago')
a_year=$(date +%Y -d ' 1  month ago')
qsub -N nci_metadata_gen \
-q  {{ params.queue }}  \
-W umask=33 \
-l wd,walltime={{ params.walltime }},mem={{ params.mem }},ncpus={{ params.ncpus }} -m abe \
-l storage=gdata/v10+scratch/v10+gdata/ka08+scratch/ka08+gdata/fj7+scratch/fj7+gdata/u46+scratch/u46 \
-P  {{ params.project }} -o {{ params.base_dir }}{{ log_ext }} -e {{ params.base_dir }}{{ log_ext }}  \
-- /bin/bash -l -c \
"module use /g/data/v10/public/modules/modulefiles/; \
module use /g/data/v10/private/modules/modulefiles/; \
module load {{ params.module }}; \
set -x; \
eo3-prepare sentinel-l1  \
--jobs {{ params.jobs_para }}  \
--after-month  $a_year-$a_month  \
--verbose \
{{ params.dry_run }}  \
{{ params.index }}  \
{{ params.config_arg }} \
--only-regions-in-file {{ params.only_regions_in_para }} \
--output-base  {{ params.output_base_para }}  \
{{ params.l1_base }} \
"
        """,
        cmd_timeout=60 * 20,
        conn_timeout=60 * 20,
        do_xcom_push=True,
    )
    # --limit-regions-file test_dont_generate.txt \

    wait_for_completion = PBSJobSensor(
        task_id="wait_for_completion",
        pbs_job_id="{{ ti.xcom_pull(task_ids='%s') }}" % submit_task_id,
        timeout=60 * 60 * 24 * 7,
    )

    start >> submit_ard >> wait_for_completion >> completed
