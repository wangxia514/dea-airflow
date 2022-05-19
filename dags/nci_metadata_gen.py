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

# I really dont want to index yet
# "index": "--index ",

params = {
    "project": "v10",
    "queue": "normal",
    "module": "eodatasets3/0.27.5",
    "index": " ",
    "months_back": "3 ",
    "jobs_para": "1",
    "config": "",
    "output_base_para": "/g/data/ka08/ga/l1c_metadata",
    "only_regions_in_para": "/g/data/v10/projects/c3_ard/dea-ard-scene-select/scene_select/data/Australian_tile_list_optimised.txt",
    "base_dir": "/g/data/v10/work/s2_c3_ard/",
    "dry_run": " ",
    "only-regions-in-file_para": "",
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


params["index"] = ""  # No indexing

# "" means no ard is produced.
params["dry_run"] = "--dry-run "

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
        pass
    else:
        params[
            "base_dir"
        ] = "/g/data/v10/Landsat-Collection-3-ops/scene_select_test_s2/"
        params["output_base_para"] = params["base_dir"] + "yaml"
        params[
            "only_regions_in_para"
        ] = "/g/data/v10/projects/c3_ard/dea-ard-scene-select/scene_select/data/region_used_by_s2_l1_yaml_gen_testing.txt"
        # "" means no ard is produced.
        # /g/data/v10/projects/c3_ard/dea-ard-scene-select/
        # scene_select/data/region_used_by_s2_l1_yaml_gen_testing.txt

else:
    pass
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
        {% set log_ext = ts_nodash %}
        """

    submit_task_id = "submit_metadata_gen"
    submit_ard = SSHOperator(
        task_id=submit_task_id,
        command=COMMON
        + """
mkdir -p {{ params.base_dir }}{{ log_ext }}
a_month=$(date +%m -d ' 6  month ago')
a_year=$(date +%Y -d ' 6  month ago')
echo ${year}
echo ${a_year}
qsub -N ard_scene_select \
-q  {{ params.queue }}  \
-W umask=33 \
-l wd,walltime=3:00:00,mem=15GB,ncpus=1 -m abe \
-l storage=gdata/v10+scratch/v10+gdata/if87+gdata/fj7+scratch/fj7+gdata/u46+scratch/u46 \
-P  {{ params.project }} -o {{ params.base_dir }}{{ log_ext }} -e {{ params.base_dir }}{{ log_ext }}  \
-- /bin/bash -l -c \
"module use /g/data/v10/public/modules/modulefiles/; \
module use /g/data/v10/private/modules/modulefiles/; \
module load {{ params.module }}; \
echo ${year}; \
echo ${a_year}; \
eo3-prepare sentinel-l1  \
--jobs  {{ params.jobs_para }}  \
--after-month $a_year-$a_month \
{{ params.dry_run }}  \
--only-regions-in-file {{ params.only_regions_in_para }} \
--output-base  {{ params.output_base_para }}  \
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
