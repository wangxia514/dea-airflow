"""
# Test DAG for submitting PBS Jobs and awaiting their completion
"""
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator

from operators.pbs_job_operator import PBSJobOperator
from sensors.pbs_job_complete_sensor import PBSJobSensor
from datetime import datetime, timedelta

default_args = {
    "owner": "Damien Ayers",
    "depends_on_past": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(
        2020, 3, 4
    ),  # probably ignored since schedule_interval is None
    "timeout": 90,  # For running SSH Commands
}

with DAG(
    "nci_test_qsub_wait",
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    template_searchpath="templates/",
    doc_md=__doc__,
) as dag:
    submit_pbs_job = PBSJobOperator(
        task_id=f"run_foo_pbs_job",
        ssh_conn_id="lpgs_gadi",
        work_dir="~/airflow_testing/",
        qsub_args="""
          -q express \
          -W umask=33 \
          -l wd,walltime=0:10:00,mem=3GB -m abe \
          -l storage=gdata/v10+gdata/fk4+gdata/rs0+gdata/if87 \
          -P {{ params.project }}  \
        """,
        qsub_command="""
          /bin/bash -l -c \
              "source $HOME/.bashrc; \
              module use /g/data/v10/public/modules/modulefiles/; \
              module load {{ params.module }}; \
              dea-coherence --check-locationless time in [2019-12-01, 2019-12-31] > coherence-out.txt"
        """,
        params={
            "project": "v10",
            "queue": "normal",
            "module": "dea/unstable",
            "year": "2019",
        },
    )
