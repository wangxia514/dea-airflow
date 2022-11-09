"""
Produce ODC metadata yaml's for S2 l1 scenes and index the scenes.
Search on NCI /g/data/fj7 for the S2 l1 scenes to index.

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
    "module": "eodatasets3/0.29.5",
    "index": "--index  ",
    "months_back": "1 ",
    "jobs_para": "1",
    "config_arg": "--config /g/data/v10/projects/c3_ard/dea-ard-scene-select/scripts/prod/ard_env/datacube.conf",
    "output_base_para": "/g/data/ka08/ga/l1c_metadata",
    "only_regions_in_para": "/g/data/v10/projects/c3_ard/dea-ard-scene-select/scene_select/data/Australian_tile_list_optimised.txt",
    "base_dir": "/g/data/v10/work/s2_c3/",
    "l1_base": "/g/data/fj7/Copernicus/Sentinel-2/MSI/L1C/",
    "dry_run": " ",
    "only-regions-in-file_para": "",
}

ssh_conn_id = "lpgs_gadi"

# schedule_interval = "0 10 * * *"
schedule_interval = None

# Having the info above as variables and some empty values
# means I can easily test by adding some test code here
# without modifying the code below.

# #/* The sed command below will remove this block of test code
# sed '/#\/\*/,/#\*\// d' nci_s2_metadata.py > ../../../nci_s2_metadata.py
# sed '/#\/\*/,/#\*\// d' dags/nci_ard/nci_s2_metadata.py > ../nci_s2_metadata.py
# mv ../nci_s2_metadata.py dags/nci_ard/nci_s2_metadata.py
# mv ../../../nci_s2_metadata.py .
# params[""] =


aws_develop = True
if aws_develop:
    # run this from airflow dev
    ssh_conn_id = "lpgs_gadi"
    # schedule_interval = "15 08 * * *"
    schedule_interval = None

    # run type
    # Options ['small_prod', 'pre_prod', 'indexing_test', 'no_indexing_test']
    # run_type = "indexing_test"
    # run_type = "indexing_ka08"
    run_type = "pre_prod"
    # Remember to blow away the db and rm old yamls
    if run_type == "small_prod":
        params["months_back"] = "1 "

    elif run_type == "pre_prod":
        # Just test that the dry-run is working
        # Have these together.
        # params["pkgdir_arg"] = "/g/data/ka08/test_ga"
        # params["index"] = " "  # no indexing

        params["months_back"] = "1 "
        params["dry_run"] = "--dry-run "

    elif run_type == "dead code":

        # The ODC db used
        params[
            "config_arg"
        ] = "--config /g/data/v10/projects/c3_ard/dea-ard-scene-select/tests/scripts/airflow/dsg547_dev.conf"
        # params["index"] = "--index "
        params["index"] = " "  # no indexing
        # params["dry_run"] = " " # produce yamls
        params["dry_run"] = "--dry-run "

    elif run_type == "indexing_test":
        params[
            "base_dir"
        ] = "/g/data/v10/Landsat-Collection-3-ops/scene_select_test_s2/"
        params["output_base_para"] = params["base_dir"] + "yaml_airflow"
        params["base_dir"] = params["base_dir"] + "/logdir/"
        params[
            "only_regions_in_para"
        ] = "/g/data/u46/users/dsg547/sandbox/processingDEA/s2_pipeline/53JQK.txt"

        # The ODC db used
        params[
            "config_arg"
        ] = "--config /g/data/u46/users/dsg547/sandbox/processingDEA/s2_pipeline/pipeline_test.conf"

        params["index"] = "--index "
        params["dry_run"] = " "
        params["months_back"] = "1 "

    elif run_type == "indexing_ka08":
        params[
            "base_dir"
        ] = "/g/data/v10/Landsat-Collection-3-ops/scene_select_test_s2/"
        params["output_base_para"] = "/g/data/ka08/ga/ga_test/l1c_metadata"
        params["base_dir"] = params["base_dir"] + "/logdir/"
        params[
            "only_regions_in_para"
        ] = "/g/data/u46/users/dsg547/sandbox/processingDEA/s2_pipeline/53JQK.txt"
        params["months_back"] = "1 "
        # params["l1_base"] = "/g/data/fj7/Copernicus/Sentinel-2/MSI/L1C/2022/2022-05/25S135E-30S140E"
        params["l1_base"] = "/g/data/fj7/Copernicus/Sentinel-2/MSI/L1C/"
        # The ODC db used
        params[
            "config_arg"
        ] = "--config /g/data/u46/users/dsg547/sandbox/processingDEA/s2_pipeline/dsg547_dev.conf"

        params["index"] = "--index "
        params["index"] = " "
        params["dry_run"] = " "
        # params["dry_run"] = "--dry-run "

    else:  # no indexing and typos go here # elif run_type == "no_indexing_test":
        params[
            "base_dir"
        ] = "/g/data/v10/Landsat-Collection-3-ops/scene_select_test_s2/"
        params["output_base_para"] = params["base_dir"] + "yaml_airflow"
        params["base_dir"] = params["base_dir"] + "/logdir/"
        params[
            "only_regions_in_para"
        ] = "/g/data/v10/projects/c3_ard/dea-ard-scene-select/scene_select/data/region_used_by_s2_l1_yaml_gen_testing.txt"

        params["index"] = ""  # No indexing
        params["dry_run"] = "--dry-run "
        params["months_back"] = "1 "

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
-l wd,walltime=3:00:00,mem=15GB,ncpus=1 -m abe \
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
