"""
# Batch Convert NetCDFs to COGs and Upload to AWS S3

This DAG runs tasks on Gadi at the NCI. It:

 * downloads an S3 inventory listing for each ODC Product,
 * compares what is in the Database with what is on S3,
 * runs a batch convert of NetCDF to COG (Inside a scheduled PBS job)
 * Uploads the COGs to S3

There is currently a manual step required before the COGs are generated.

Once the list of files to create is checked checked, the
`manual_sign_off_<product-name>` task should be selected, and marked as **Success**
for the DAG to continue running.

"""
import os
from datetime import datetime, timedelta
from textwrap import dedent

from airflow import DAG, AirflowException
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.models import Variable
from airflow.operators.python_operator import PythonOperator

from operators.ssh_operators import ShortCircuitSSHOperator
from sensors.pbs_job_complete_sensor import PBSJobSensor

DEST = os.environ.get(
    "COG_OUTPUT_DESTINATION",
    "s3://dea-public-data/"
)

# Default to the stable dea module on the NCI, but can be changed
# using an Airflow variable
NCI_MODULE = Variable.get("nci_module", "dea")

# TODO: This is duplicated from the configuration file for dea-cogger
# It's much better to specify a more specific path in S3 otherwise sync
# seems to try to traverse the whole bucket.
COG_S3PREFIX_PATH = {
    'wofs_albers': 'WOfS/WOFLs/v2.1.5/combined/',
    'ls8_fc_albers': 'fractional-cover/fc/v2.2.1/ls8/',
    'ls7_fc_albers': 'fractional-cover/fc/v2.2.1/ls7/'
}

TIMEOUT = timedelta(days=1)


def task_to_fail():
    """Make a Task into a manual Check

    Raise an exception with a message asking for this Task to be manually marked
    as successful.
    """
    raise AirflowException("Please change this step to success to continue")


default_args = {
    'owner': 'dayers',
    'start_date': datetime(2020, 3, 12),
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    'ssh_conn_id': 'lpgs_gadi',
    'email': 'damien.ayers@ga.gov.au',
    'email_on_failure': True,
    'params': {
        'project': 'v10',
        'queue': 'normal',
        'module': NCI_MODULE,
        'year': '2020'
    }
}

dag = DAG(
    'nci_cog_and_upload',
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    template_searchpath='templates/',
    max_active_runs=1,
    default_view='graph',
    tags=['nci', 'landsat_c2'],
)

with dag:
    for product, prefix_path in COG_S3PREFIX_PATH.items():
        COMMON = """
                {% set work_dir = '/g/data/v10/work/cog/' + params.product + '/' + ts_nodash -%}
                module load {{params.module}}
                set -eux"""
        download_s3_inventory = SSHOperator(
            task_id=f'download_s3_inventory_{product}',
            command=dedent(COMMON + '''
                mkdir -p {{work_dir}}

                dea-cogger save-s3-inventory --product-name "{{ params.product }}" --output-dir "{{work_dir}}"
            '''),
            params={'product': product},
        )
        generate_work_list = SSHOperator(
            task_id=f'generate_work_list_{product}',
            command=dedent(COMMON + """
                cd {{work_dir}}

                dea-cogger generate-work-list --product-name "{{params.product}}" \\
                 --output-dir "{{work_dir}}" --s3-list  "{{params.product}}_s3_inv_list.txt" \\
                 --time-range "time in [2019-01-01, 2020-12-31]"
            """),
            # --time-range "time in [{{prev_ds}}, {{ds}}]"
            timeout=60 * 60 * 2,
            params={'product': product},
        )
        check_for_work = ShortCircuitSSHOperator(
            task_id=f'check_for_work_{product}',
            command=dedent(COMMON + '''
                {% set file_list = work_dir + '/' + params.product + '_file_list.txt' -%}
                
                test -f {{file_list}}
                NUM_TO_PROCESS=$(wc -l {{file_list}} | awk '{print $1}')
                echo There are $NUM_TO_PROCESS files to process.
                test $NUM_TO_PROCESS -gt 0
                '''),
            params={'product': product},
        )
        # Thanks https://stackoverflow.com/questions/48580341/how-to-add-manual-tasks-in-an-apache-airflow-dag
        # manual_sign_off = PythonOperator(
        #     task_id=f"manual_sign_off_{product}",
        #     python_callable=task_to_fail,
        #     retries=1,
        #     retry_delay=TIMEOUT,
        # )
        # manual_sign_off.doc_md = dedent("""
        #         ## Instructions
        #         Perform some manual checks that the number of COGs to be generated seems to be about right.
                
        #         You can also do spot checks that files don't already exist in S3.
                
        #         Once you're happy, mark this job as **Success** for the DAG to continue running.
        #     """)
        submit_task_id = f'submit_cog_convert_job_{product}'
        submit_bulk_cog_convert = SSHOperator(
            task_id=submit_task_id,
            command=dedent(COMMON + """
                cd {{work_dir}}
                mkdir -p out
                
                qsub <<EOF
                #!/bin/bash
                #PBS -l wd,walltime=5:00:00,mem=190GB,ncpus=48,jobfs=1GB
                #PBS -P {{params.project}}
                #PBS -q {{params.queue}}
                #PBS -l storage=gdata/v10+gdata/fk4+gdata/rs0+gdata/if87
                #PBS -W umask=33
                #PBS -N cog_{{params.product}} 
                
        
                module load {{params.module}}
                module load openmpi/3.1.4

                mpirun --tag-output dea-cogger mpi-convert --product-name "{{params.product}}" \\
                 --output-dir "{{work_dir}}/out/" {{params.product}}_file_list.txt
                
                EOF
            """),
            do_xcom_push=True,
            timeout=60 * 5,
            params={'product': product},
        )

        wait_for_cog_convert = PBSJobSensor(
            task_id=f'wait_for_cog_convert_{product}',
            pbs_job_id="{{ ti.xcom_pull(task_ids='%s') }}" % submit_task_id,
            timeout=60 * 60 * 24 * 7,
        )

        validate_task_id = f'submit_validate_cog_job_{product}'
        validate_cogs = SSHOperator(
            task_id=validate_task_id,
            command=dedent(COMMON + """
                cd {{work_dir}}
                
                qsub <<EOF
                #!/bin/bash
                #PBS -l wd,walltime=5:00:00,mem=190GB,ncpus=48,jobfs=1GB
                #PBS -P {{params.project}}
                #PBS -q {{params.queue}}
                #PBS -l storage=gdata/v10+gdata/fk4+gdata/rs0+gdata/if87
                #PBS -W umask=33
                #PBS -N cog_{{params.product}} 
                
        
                module load {{params.module}}
                module load openmpi/3.1.4

                mpirun --tag-output dea-cogger verify --rm-broken "{{work_dir}}/out"
                
                EOF
            """),
            do_xcom_push=True,
            timeout=60 * 5,
            params={'product': product},
        )
        wait_for_validate_job = PBSJobSensor(
            task_id=f'wait_for_cog_validate_{product}',
            pbs_job_id="{{ ti.xcom_pull(task_ids='%s') }}" % validate_task_id,
            timeout=60 * 60 * 24 * 7,

        )

        # public_data_upload = Connection(conn_id='dea_public_data_upload')
        aws_connection = AwsHook(aws_conn_id='dea_public_data_upload')
        upload_to_s3 = SSHOperator(
            task_id=f'upload_to_s3_{product}',
            command=dedent(COMMON + """

            export AWS_ACCESS_KEY_ID={{params.aws_conn.access_key}}
            export AWS_SECRET_ACCESS_KEY={{params.aws_conn.secret_key}}

            # See what AWS creds we've got
            aws sts get-caller-identity
            
            aws s3 sync "{{work_dir}}/out/{{ params.prefix_path }}" {{ params.dest }}{{ params.prefix_path }} \\
            --exclude '*.yaml'
            
            # Upload YAMLs second, and only if uploading the COGs worked
            aws s3 sync "{{work_dir}}/out/{{ params.prefix_path }}" {{ params.dest }}{{ params.prefix_path }} \\
            --exclude '*' --include '*.yaml'
            """),
            remote_host='gadi-dm.nci.org.au',
            params={'product': product,
                    'aws_conn': aws_connection.get_credentials(),
                    'dest': DEST,
                    'prefix_path': prefix_path},
        )

        delete_nci_cogs = SSHOperator(
            task_id=f'delete_nci_cogs_{product}',
            # Remove cog converted files after aws s3 sync
            command=dedent(COMMON + """
            rm -vrf "{{work_dir}}/out"
            """),
            params={'product': product},
        )

        download_s3_inventory >> generate_work_list >> check_for_work >> submit_bulk_cog_convert
        submit_bulk_cog_convert >> wait_for_cog_convert >> validate_cogs >> wait_for_validate_job
        wait_for_validate_job >> upload_to_s3 >> delete_nci_cogs
