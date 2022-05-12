"""
# Produce Landsat C3 ARD on the NCI

The DAG starts ard_scene_select which filters the landsat l1 scenes to send to ARD to process.
It also starts the ARD processing.  ARD processing indexes the ARD output scenes.

The logs are written to NCI.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.operators.dummy import DummyOperator

from sensors.pbs_job_complete_sensor import PBSJobSensor

params = {
    "project": "v10",
    "queue": "normal",
    "module": "eodatasets3/0.27.4",
    "index_arg": "--index-datacube-env "
    "/g/data/v10/projects/c3_ard/dea-ard-scene-select/scripts/prod/ard_env/index-datacube.env",
    "wagl_env": "/g/data/v10/projects/c3_ard/dea-ard-scene-select/scripts/prod/ard_env/prod-wagl-s2.env",
    "config_arg": "",
    "scene_limit": "--scene-limit 400",
    "interim_days_wait": "",
    "products_arg": """--products '["esa_s2am_level1_1", "esa_s2bm_level1_1"]'""",
    "pkgdir_arg": "/g/do/not/know/",
    "base_dir": "/g/data/v10/work/s2_c3_ard/",
    "days_to_exclude_arg": "",
    "run_ard_arg": "--run-ard",
    "yamldir": " --yamls-dir /g/data/u46/users/dsg547/test_data/s2_pipeline/yaml/",
}

ssh_conn_id = "lpgs_gadi"
schedule_interval = "0 10 * * *"

# Having the info above as variables and some empty values
# means I can easily test by adding some test code here
# without modifying the code below.

# #/* The sed command below will remove this block of test code
# sed '/#\/\*/,/#\*\// d' nci_ard.py > ../../nci_ard.py
# sed '/#\/\*/,/#\*\// d' dags/nci_ard.py > ../nci_ard.py
# mv ../nci_ard.py dags/nci_ard.py
# params[""] =

params["index_arg"] = ""  # No indexing

# "" means no ard is produced.
params["run_ard_arg"] = ""

use_test_db = True
if use_test_db:
    params[
        "index_arg"
    ] = "--index-datacube-env /g/data/v10/projects/c3_ard/dea-ard-scene-select/tests/scripts/airflow/index-test-odc.env"

    # This will be updated when the production code is updated.
    params[
        "config_arg"
    ] = "--config /g/data/v10/projects/c3_ard/dea-ard-scene-select/tests/scripts/airflow/pipeline_test.conf"
    # until then run from the dev code

# params["days_to_exclude_arg"] = ""
#  if you use it it looks like """--days-to-exclude '["2020-06-26:2020-06-26"]'"""

params["run_ard_arg"] = ""

aws_develop = True
if aws_develop:
    # run this from airflow dev
    ssh_conn_id = "lpgs_gadi"
    # schedule_interval = "15 08 * * *"
    schedule_interval = None

    # Use yamls from the test dir
    params[
        "yamldir"
    ] = " --yamls-dir /g/data/u46/users/dsg547/test_data/s2_pipeline/yaml/"
    small_prod_run = False  # small_prod_run or small_non_prod
    if small_prod_run:
        params["index_arg"] = "--index-datacube-env "
        params["pkgdir_arg"] = params["base_dir"]
        params["scene_limit"] = "--scene-limit 1"
    else:
        params[
            "pkgdir_arg"
        ] = "/g/data/v10/Landsat-Collection-3-ops/scene_select_test_s2/"
        # "" means no ard is produced.
        params["run_ard_arg"] = ""

    # A fail safe
    # params["scene_limit"] = "--scene-limit 1"
    #
else:
    # run this from local dev
    # Add the storage for u46 back
    # -l storage=gdata/v10+scratch/v10+gdata/if87+gdata/fj7+scratch/fj7+scratch/u46+gdata/u46 \

    ssh_conn_id = "dsg547"
    params["project"] = "u46"
    params["pkgdir_arg"] = "/g/data/u46/users/dsg547/results_airflow/"
    schedule_interval = None
params["base_dir"] = params["pkgdir_arg"]
# #*/ The end of the sed removed block of code

default_args = {
    "owner": "Duncan Gray",
    "depends_on_past": False,  # Very important, will cause a single failure to propagate forever
    "start_date": datetime(2022, 5, 10),
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
    "ssh_conn_id": ssh_conn_id,
    "params": params,
}

dag = DAG(
    "nci_metadata_gen",
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval=schedule_interval,
    default_view="tree",
    tags=["nci", "s2_c3"],
)

with dag:
    start = DummyOperator(task_id="start")
    completed = DummyOperator(task_id="completed")

    COMMON = """
        #  ts_nodash timestamp no dashes.
        {% set log_ext = ts_nodash + '/logdir' %}
        {% set work_ext = ts_nodash + '/workdir' %}
        """

    submit_task_id = "submit_metadata_gen"
    submit_ard = SSHOperator(
        task_id=submit_task_id,
        command=COMMON
        + """
        qsub -N ard_scene_select \
              -q  {{ params.queue }}  \
              -W umask=33 \
              -l wd,walltime=3:00:00,mem=15GB,ncpus=1 -m abe \
              -l storage=gdata/v10+scratch/v10+gdata/if87+gdata/fj7+scratch/fj7+gdata/u46+scratch/u46 \
              -P  {{ params.project }} -o {{ params.base_dir }}{{ log_ext }} -e {{ params.base_dir }}{{ log_ext }}  \
              -- /bin/bash -l -c \
                  "module use /g/data/v10/public/modules/modulefiles/; \
                  module use /g/data/v10/private/modules/modulefiles/; \
                  module use /g/data/u46/users/dsg547/devmodules/modulefiles/; \
                  module load {{ params.module }}; \
                  eo3-prepare sentinel-l1  --help; \
                  eo3-prepare sentinel-l1  \
                  -j 4 --after-month 2022-05 \
                  --dry-run \
                  --output-base  /g/data/u46/users/dsg547/test_data/s2_pipelineII/c3/L1C \
                  /g/data/fj7/Copernicus/Sentinel-2/MSI/L1C/2022"
        """,
        timeout=60 * 20,
        do_xcom_push=True,
    )
    # --limit-regions-file test_dont_generate.txt \

    wait_for_completion = PBSJobSensor(
        task_id="wait_for_completion",
        pbs_job_id="{{ ti.xcom_pull(task_ids='%s') }}" % submit_task_id,
        timeout=60 * 60 * 24 * 7,
    )

    start >> submit_ard >> wait_for_completion >> completed
