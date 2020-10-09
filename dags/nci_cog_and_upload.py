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
import logging
import os
from datetime import timedelta
from textwrap import dedent

from airflow import DAG
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.python_operator import ShortCircuitOperator
from airflow.operators.sensors import ExternalTaskSensor

from nci_common import c2_default_args, c2_schedule_interval
from sensors.pbs_job_complete_sensor import PBSJobSensor

DEST = os.environ.get(
    "COG_OUTPUT_DESTINATION",
    "s3://dea-public-data/"
)

# TODO: This is duplicated from the configuration file for dea-cogger
# It's much better to specify a more specific path in S3 otherwise sync
# seems to try to traverse the whole bucket.
COG_S3PREFIX_PATH = {
    'wofs_albers': 'WOfS/WOFLs/v2.1.5/combined/',
    'ls8_fc_albers': 'fractional-cover/fc/v2.2.1/ls8/',
    'ls7_fc_albers': 'fractional-cover/fc/v2.2.1/ls7/'
}

TIMEOUT = timedelta(days=1)


def check_num_tasks(upstream_task_id, ti, **kwargs):
    """ Check the number of COG tasks to complete

    Short circuit if there are none. Ask for manual verification if there are lots,
    otherwise continue.
    """
    response = ti.xcom_pull(task_ids=upstream_task_id)
    last_line = response.split('\n')
    num_tasks = int(last_line)

    if num_tasks == 0:
        logging.info("Nothing to do, stopping.")
        return False
    elif num_tasks >= 1000:
        # TODO: Maybe send email as well
        logging.info(
            "Please review, this looks like an unusually large number of COGs to generate. "
            "If correct, set this task to success.")
        return False

    # Otherwise, carry on
    return num_tasks


dag = DAG(
    'nci_cog_and_upload',
    doc_md=__doc__,
    default_args=c2_default_args,
    catchup=False,
    schedule_interval=c2_schedule_interval,
    template_searchpath='templates/',
    default_view='tree',
    tags=['nci', 'landsat_c2'],
)

with dag:
    for product, prefix_path in COG_S3PREFIX_PATH.items():
        COMMON = dedent("""
                {% set work_dir = '/g/data/v10/work/cog/' + params.product + '/' + ts_nodash -%}
                module load {{params.module}}
                set -eux
        """)

        if 'wofs' in product:
            external_dag_id = 'nci_wofs'
            external_task_id = None
        else:
            external_dag_id = 'nci_fractional_cover'
            external_task_id = f'wait_for_{product}'
        processing_completed = ExternalTaskSensor(
            task_id=f'processing_completed_{product}',
            external_dag_id=external_dag_id,
            external_task_id=external_task_id
        )

        download_s3_inventory = SSHOperator(
            task_id=f'download_s3_inventory_{product}',
            command=COMMON + dedent('''
                mkdir -p {{work_dir}}

                dea-cogger save-s3-inventory --product-name "{{ params.product }}" --output-dir "{{work_dir}}"
            '''),
            params={'product': product},
        )
        generate_work_list = SSHOperator(
            task_id=f'generate_work_list_{product}',
            command=COMMON + dedent("""
                cd {{work_dir}}

                dea-cogger generate-work-list --product-name "{{params.product}}" \\
                 --output-dir "{{work_dir}}" --s3-list  "{{params.product}}_s3_inv_list.txt" \\
                 --time-range "time in [2019-01-01, 2020-12-31]"
            """),
            # --time-range "time in [{{prev_ds}}, {{ds}}]"
            timeout=60 * 60 * 2,
            params={'product': product},
        )
        count_num_tasks = SSHOperator(
            task_id=f'count_num_tasks_{product}',
            command=COMMON + dedent('''
                {% set file_list = work_dir + '/' + params.product + '_file_list.txt' -%}
                test -f {{file_list}}
                wc -l {{file_list}} | awk '{print $1}'
            '''),
            params={'product': product},
            do_xcom_push=True
        )
        # Thanks https://stackoverflow.com/questions/48580341/how-to-add-manual-tasks-in-an-apache-airflow-dag
        check_for_work = ShortCircuitOperator(
            task_id=f"check_for_work_{product}",
            python_callable=check_num_tasks,
            op_args=[f'check_work_file_{product}'],
            provide_context=True,
        )
        check_for_work.doc_md = dedent("""
                ## Instructions
                Perform some manual checks that the number of COGs to be generated seems to be about right.

                You can also do spot checks that files don't already exist in S3.

                Once you're happy, mark this job as **Success** for the DAG to continue running.
            """)
        submit_task_id = f'submit_cog_convert_job_{product}'
        submit_bulk_cog_convert = SSHOperator(
            task_id=submit_task_id,
            command=COMMON + dedent("""
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
            command=COMMON + dedent("""
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

        aws_connection = AwsHook(aws_conn_id='dea_public_data_upload')
        upload_to_s3 = SSHOperator(
            task_id=f'upload_to_s3_{product}',
            command=COMMON + dedent("""
            {% set aws_creds = params.aws_conn.get_credentials() -%}

            export AWS_ACCESS_KEY_ID={{aws_creds.access_key}}
            export AWS_SECRET_ACCESS_KEY={{aws_creds.secret_key}}

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
                    'aws_conn': aws_connection,
                    'dest': DEST,
                    'prefix_path': prefix_path},
        )

        # Remove cog converted files after aws s3 sync
        delete_nci_cogs = SSHOperator(
            task_id=f'delete_nci_cogs_{product}',
            command=COMMON + dedent("""
            rm -vrf "{{work_dir}}/out"
            """),
            params={'product': product},
        )

        processing_completed >> download_s3_inventory
        download_s3_inventory >> generate_work_list >> count_num_tasks >> check_for_work >> submit_bulk_cog_convert
        submit_bulk_cog_convert >> wait_for_cog_convert >> validate_cogs >> wait_for_validate_job
        wait_for_validate_job >> upload_to_s3 >> delete_nci_cogs
