"""
# Produce Landsat C3 ARD on the NCI

The DAG starts ard_scene_select which filters the landsat l1 scenes to send to ARD to process.
It also starts the ARD processing.  ARD processing indexes the ARD output scenes.

The logs are written to NCI.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.dummy_operator import DummyOperator

from sensors.pbs_job_complete_sensor import PBSJobSensor

# swap around set work_dir log_dir too
production = False

if production:
    params = {
        "project": "v10",
        "queue": "normal",
        "module_ass": "ard-scene-select-py3-dea/20200831",
        "index_arg": "--index-datacube-env "
        "/g/data/v10/projects/c3_ard/dea-ard-scene-select/scripts/prod/ard_env/index-datacube.env",
        "wagl_env": "/g/data/v10/projects/c3_ard/dea-ard-scene-select/scripts/prod/ard_env/prod-wagl.env",
        "config_arg": "",
        "scene_limit": "",
        "products_arg": "",
        "pkgdir_arg": "/g/data/xu18/ga",
    }
else:
    params = {
        "project": "u46",
        "queue": "normal",
        "module_ass": "ard-scene-select-py3-dea/20200831",
        "index_arg": "--index-datacube-env /g/data/v10/projects/c3_ard/dea-ard-scene-select/tests/scripts/airflow"
        "/index-test-odc.env",
        # "index_arg": "",  # no indexing
        "wagl_env": "/g/data/v10/projects/c3_ard/dea-ard-scene-select/scripts/prod/ard_env/prod-wagl.env",
        "config_arg": "--config /g/data/v10/projects/c3_ard/dea-ard-scene-select/tests/scripts/airflow/dsg547_dev.conf",
        "scene_limit": "--scene-limit 1",
        "products_arg": """--products '["usgs_ls8c_level1_1"]'""",
        "pkgdir_arg": "/g/data/v10/Landsat-Collection-3-ops/scene_select_test/",
    }

default_args = {
    "owner": "Duncan Gray",
    "depends_on_past": False,  # Very important, will cause a single failure to propagate forever
    "start_date": datetime(2020, 8, 26),
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
    "ssh_conn_id": "lpgs_gadi",
    # "ssh_conn_id': 'dsg547",
    "params": params,
}

# tags is in airflow >1.10.8
# My local env is airflow 1.10.10...
dag = DAG(
    "nci_test_ard",
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    default_view="graph",
    tags=["nci", "landsat_c3"],
)

with dag:
    start = DummyOperator(task_id="start")
    completed = DummyOperator(task_id="completed")

    COMMON = """
        #  ts_nodash timestamp no dashes.
        {% set log_dir = '/g/data/v10/Landsat-Collection-3-ops/scene_select_test/' + ts_nodash + '/logdir' %}
        {% set work_dir = '/g/data/v10/Landsat-Collection-3-ops/scene_select_test/' + ts_nodash + '/workdir' %}
        {% set log_dir = '/g/data/v10/work/c3_ard/' + ts_nodash + '/logdir' %}
        {% set work_dir = '/g/data/v10/work/c3_ard/' + ts_nodash + '/workdir' %}
        {% set log_dir = '/g/data/u46/users/dsg547/results_airflow/' + ts_nodash + '/logdir' %}
        {% set work_dir = '/g/data/u46/users/dsg547/results_airflow/' + ts_nodash + '/workdir' %}
        {% set log_dir = '/g/data/v10/Landsat-Collection-3-ops/scene_select_test/' + ts_nodash + '/logdir' %}
        {% set work_dir = '/g/data/v10/Landsat-Collection-3-ops/scene_select_test/' + ts_nodash + '/workdir' %}
        """

    # An example of remotely starting a qsub job (all it does is ls)
    submit_task_id = f"submit_ard"
    submit_ard = SSHOperator(
        task_id=submit_task_id,
        command=COMMON
        + """
        mkdir -p {{ log_dir }} 
        mkdir -p {{ work_dir }} 
        qsub -N ard_scene_select \
              -q  {{ params.queue }}  \
              -W umask=33 \
              -l wd,walltime=0:30:00,mem=15GB,ncpus=1 -m abe \
              -l storage=gdata/v10+scratch/v10+gdata/if87+gdata/fj7+scratch/fj7+scratch/u46+gdata/u46 \
              -P  {{ params.project }} -o {{ log_dir }} -e {{ log_dir }}  \
              -- /bin/bash -l -c \
                  "module use /g/data/v10/public/modules/modulefiles/; \
                  module use /g/data/v10/private/modules/modulefiles/; \
                  module load {{ params.module_ass }}; \
                  ard-scene-select \
                {{ params.products_arg }} \
                {{ params.config_arg }} \
                  --workdir {{ work_dir }} \
                  --pkgdir {{ params.pkgdir_arg }} \
                  --logdir {{ log_dir }} \
                  --env {{ params.wagl_env }}  \
                  --project {{ params.project }} \
                  --walltime 02:30:00 \
                  {{ params.index_arg }} \
                  {{ params.scene_limit }}\
                  --run-ard "
        """,
        timeout=60 * 20,
        do_xcom_push=True,
    )

    wait_for_completion = PBSJobSensor(
        task_id=f"wait_for_completion",
        pbs_job_id="{{ ti.xcom_pull(task_ids='%s') }}" % submit_task_id,
        timeout=60 * 60 * 24 * 7,
    )

    start >> submit_ard >> wait_for_completion >> completed
