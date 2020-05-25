"""
# Indexing Sentinel 2 ARD Data on the NCI

This DAG is responsible for crawing the NCI file system for completed Sentinel 2 ARD granules
and adding them to the NCI Open Data Cube Index.

This is both more complicated and flakier due to the time and cost crawling the Lustre filesystem
used for `/g/data`, it is a distributed network filesystem and has performance characteristics
more in common with an object store.

I originally wanted to make this DAG deterministic, based on file modification dates, but this is
too slow.

Switching back to making it process any directories modified in the last 60 days.

"""

from textwrap import dedent

from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator

from sensors.pbs_job_complete_sensor import PBSJobSensor

default_args = {
    'owner': 'dayers',
    'depends_on_past': False,
    'start_date': datetime(2020, 4, 1),
    'email': ['damien.ayers@ga.gov.au'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'params': {
        'project': 'v10',
        'module': 'dea/unstable',
        'queue': 'normal',
    }
}

with DAG('nci_index_s2ard',
         default_args=default_args,
         catchup=True,
         schedule_interval=timedelta(days=7),
         max_active_runs=2,
         doc_md=__doc__,
         ) as dag:

    index_datasets = SSHOperator(
        task_id=f'index_datasets',
        ssh_conn_id='lpgs_gadi',
        command=dedent('''
        set -eu
        module load dea/unstable
        
        cd /g/data/if87/datacube/002/S2_MSI_ARD/packaged

        today=$(date -I)

        dates=()
        for i in {0..120}; do 
            new_date=$(date -I -d "$today -$i days")
            if [[ -d $new_date ]]; then
                dates+=( $new_date )
            fi
        done
        
        # Find all the directories for captures from the last 120 days.
        # Not every day will exist yet, and not every day will ever exist (eg. satellite didn't pass over Australia
        # on that day).
        
        # We could probably use `ls` instead of `find` here, but I was using find.
        # Use sed to append the known metadata file name instead of doing yet another (slow) directory retrieval.
        
        # This entire process takes around 2.5 seconds for a 120 day period, in testing on 2020-05-25 on gadi.
        
        # Whereas using the following took 1m40s for the same 120 days.
        # Using `find ${dates[@]} -maxdepth 2 -name 'ARD-METADATA.yaml' | wc -l` as a command with the 

        find ${dates[@]} -maxdepth 1 -mindepth 1 | sed 's|$|/ARD-METADATA.yaml|' | xargs datacube dataset add
        
        '''),
    )

