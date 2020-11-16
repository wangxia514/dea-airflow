"""
# Sentinel-2 data routine sync to S3 bucket

This DAG runs tasks on Gadi at the NCI. This DAG routinely sync Sentinel-2
data from NCI to AWS S3 bucket. It:

 * Uploads `Sentinel-2 to S3 rolling` script to NCI work folder.
 * Executes uploaded rolling script to upload `Sentinel-2` data to AWS `S3` bucket.
 * Cleans working folder at `NCI` after upload completion.

This DAG takes following input parameters from `nci_s2_upload_s3_config` variable:

 * `s3bucket`: Name of the S3 bucket. `"dea-public-data"`
 * `doupdate`: Select update option as below to replace granules and metadata.
    * `'granule_metadata'` to update granules and metadata;
    * `'granule' to update'` granules without metadata;
    * `'metadata'` to update only metadata;
    * `'no'` or don't set to avoid update of existing granules/metadata..
"""
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent

import pendulum
from airflow import DAG, configuration
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.sftp_operator import SFTPOperator, SFTPOperation
from airflow.contrib.operators.ssh_operator import SSHOperator

from nci_common import HOURS, MINUTES

local_tz = pendulum.timezone("Australia/Canberra")

# language=SQL
# SQL_QUERY = """SELECT dsl.uri_body, ds.archived, ds.added,
#     to_timestamp({{ next_execution_date.timestamp() }}) at time zone 'Australia/Canberra' as exec_dt
#     FROM agdc.dataset ds
#     INNER JOIN agdc.dataset_type dst ON ds.dataset_type_ref = dst.id
#     INNER JOIN agdc.dataset_location dsl ON ds.id = dsl.dataset_ref
#     WHERE dst.name='{{ params.product }}'
#         AND (ds.added BETWEEN
#                 (to_timestamp({{ execution_date.timestamp() }}) at time zone 'Australia/Canberra')
#                 AND (to_timestamp({{ next_execution_date.timestamp() }}) at time zone 'Australia/Canberra')
#             OR ds.archived BETWEEN
#                 (to_timestamp({{ execution_date.timestamp() }}) at time zone 'Australia/Canberra')
#                 AND (to_timestamp({{ next_execution_date.timestamp() }}) at time zone 'Australia/Canberra') ) ;"""

# language="Shell Script"
COMMON = dedent("""
        {% set work_dir = '/g/data/v10/work/s2_nbar_rolling_archive/' + ds  -%}
        mkdir -p {{work_dir}}
        cd {{ work_dir }}

        # echo on and exit on fail
        set -eu

        # Load the latest stable DEA module
        module use /g/data/v10/public/modules/modulefiles
        module load dea

        # Be verbose and echo what we run
        set -x
""")

default_args = {
    'owner': 'Damien Ayers',
    'start_date': datetime(2019, 12, 6, tzinfo=local_tz),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': True,
    'email': 'damien.ayers@ga.gov.au',
    'ssh_conn_id': 'lpgs_gadi',
    'aws_conn_id': 'dea_public_data_upload',
}

dag = DAG(
    'nci_s2_upload_s3',
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval='@daily',
    max_active_runs=4,
    default_view='tree',
    tags=['nci', 'sentinel_2'],
)

with dag:
    # # language=Python
    # PYTHON_SCRIPT = dedent("""
    #         from datacube import Datacube
    #         dc = Datacube()
    #         engine = dc.index._db._engine
    #         result = engine.execute('''INSERT_QUERY_HERE''')
    #         ids = [id for id, in result]
    #         datasets = dc.index.datasets.bulk_get(ids)
    #         for dataset in datasets:
    #             # return f"s3://dea-public-data/L2/sentinel-2-nbar/S2MSIARD_NBAR/{ds.key_time.strftime('%Y-%m-%d')}/{ds.metadata_doc['tile_id'].replace('L1C', 'ARD')}/ARD-METADATA.yaml"
    #             # Don't trust the datetimes that are exposed!
    #             print(f"s3://dea-public-data/L2/sentinel-2-nbar/S2MSIARD_NBAR/{ds.metadata_doc['extent']['center_dt'][:10]}/{ds.metadata_doc['tile_id'].replace('L1C', 'ARD')}/ARD-METADATA.yaml")
    # """)
    # PYTHON_SCRIPT = PYTHON_SCRIPT.replace('INSERT_QUERY_HERE', SQL_QUERY)
    # Uploading s2_to_s3_rolling.py script to NCI
    upload_uploader_script = SFTPOperator(
        task_id="upload_uploader_script",
        local_filepath=str(Path(configuration.get('core', 'dags_folder')).parent / "scripts/upload_s2.py"),
        remote_filepath="/g/data/v10/work/s2_nbar_rolling_archive/{{ds}}/upload_s2.py",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True
    )
    # language="Shell Script"
    generate_list = SSHOperator(
        task_id='generate_list_of_s2_to_upload',
        # python - <<EOF > s3_paths_list.txt
        # {PYTHON_SCRIPT}
        # EOF
        # language="Shell Script"
        command=COMMON + dedent("""
        
            for product_name in s2a_ard_granule, s2b_ard_granule; do
                echo Searching for $product_name datasets.
            psql --variable=ON_ERROR_STOP=1 --csv --quiet --tuples-only --no-psqlrc -h dea-db.nci.org.au datacube <<EOF >> s3_paths_list.txt
            SELECT 's3://dea-public-data/L2/sentinel-2-nbar/S2MSIARD_NBAR/' 
                    || substring(ds.metadata#>>'{extent,center_dt}' for 10) || '/' 
                    || replace(ds.metadata#>>'{tile_id}', 'L1C', 'ARD') || '/ARD-METADATA.yaml'
                FROM agdc.dataset ds
                INNER JOIN agdc.dataset_type dst ON ds.dataset_type_ref = dst.id
                INNER JOIN agdc.dataset_location dsl ON ds.id = dsl.dataset_ref
                WHERE dst.name='$product_name'
                  AND ds.added BETWEEN '{{ prev_execution_date }}' AND '{{ next_execution_date }}'
                   OR ds.archived BETWEEN '{{ prev_execution_date }}' AND '{{ next_execution_date }}';
            EOF
            done

            echo -n Num Datasets to upload: 
            wc -l s3_paths_list.txt
        
        """),
        remote_host='gadi-dm.nci.org.au',
        timeout=20 * MINUTES,
    )

    # Execute script to upload sentinel-2 data to s3 bucket
    aws_hook = AwsHook(aws_conn_id=dag.default_args['aws_conn_id'])
    execute_upload = SSHOperator(
        task_id='execute_upload',
        # language="Shell Script"
        command=dedent(COMMON + """
            {% set aws_creds = params.aws_hook.get_credentials() -%}

            # Export AWS Access key/secret from Airflow connection module
            export AWS_ACCESS_KEY_ID={{aws_creds.access_key}}
            export AWS_SECRET_ACCESS_KEY={{aws_creds.secret_key}}

            python3 '{{ work_dir }}/upload_s2.py' s3_paths_list.txt
        """),
        remote_host='gadi-dm.nci.org.au',
        params={'aws_hook': aws_hook},
        timeout=10 * HOURS,
    )
    [upload_uploader_script, generate_list] >> execute_upload
