"""
# Sentinel-2 data routine upload to S3 bucket

This DAG runs tasks on Gadi at the NCI. This DAG routinely sync Sentinel-2
data from NCI to AWS S3 bucket. It:

 * Creates necessary working folder at `NCI`.
 * Uploads `Sentinel-2 to S3 rolling` script to NCI work folder.
 * Executes uploaded rolling script to upload `Sentinel-2` data to AWS `S3` bucket. The upload takes
 place for yesterday of the DAG's execution date. E.g. For execution date `"2020-05-15"`, the
 upload process will take place for `"2020-05-14"` (a day before execution date).
 * Cleans working folder at `NCI` after upload completion.

This DAG takes following input parameters from `"nci_s2_upload_s3_config"` variable:

 * `start_date`: Start date for DAG run.
 * `end_date`: End date for DAG run.
 * `catchup`: Set to "True" for back fill else "False".
 * `schedule_interval`: Set "" for no schedule else provide schedule cron or preset (@once, @daily).
 * `ssh_conn_id`: Provide SSH Connection ID.
 * `aws_conn_id`: Provide AWS Conection ID.
 * `s3bucket`: Name of the S3 bucket.
 * `numdays`: Number of days to process before the execution date.
 * `doupdate`: Select update option as below to enable replace granules and metadata.
            If update option is not provided, granules and metadata are not synced
            if they already exists in S3 bucket
    * `'granule_metadata'` to update granules with metadata;
    * `'granule' to update'` granules without metadata;
    * `'metadata'` to update only metadata;
    * `'no'` or don't set to avoid update.

**EXAMPLE** *- Variable in JSON format with key name "nci_s2_upload_s3_config":*

    {
        "nci_s2_upload_s3_config":
        {
            "start_date": "2020-4-1",
            "end_date": "2020-4-30",
            "catchup": "False",
            "schedule_interval" : "@daily",
            "ssh_conn_id": "lpgs_gadi",
            "aws_conn_id": "dea_public_data_dev_upload",
            "s3bucket": "dea-public-data-dev",
            "numdays": "0",
            "doupdate": "no"
        }
    }
"""
from datetime import datetime, timedelta
from textwrap import dedent
from pathlib import Path

from airflow import DAG, configuration
from airflow.models import Variable
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.contrib.operators.sftp_operator import SFTPOperator, SFTPOperation


# Read and load variable into dict
VARIABLE_NAME = "nci_s2_upload_s3_config"
dag_config = Variable.get(VARIABLE_NAME, deserialize_json=True)


def get_parameter_value_from_variable(_dag_config, parameter_name, default_value=''):
    """
    Return parameter value from variable
    :param _dag_config: Name of the variable
    :param parameter_name: Parameter name
    :param default_value: Default value if parameter is empty
    :return: Parameter value for provided parameter name
    """
    if parameter_name in _dag_config and _dag_config[parameter_name]:
        parameter_value = _dag_config[parameter_name]
    elif default_value != '':
        parameter_value = default_value
    else:
        raise Exception("Missing necessary parameter '{}' in "
                        "variable '{}'".format(parameter_name, VARIABLE_NAME))
    return parameter_value


default_args = {
    'owner': 'Sachit Rajbhandari',
    'start_date': get_parameter_value_from_variable(dag_config, 'start_date', datetime.today()),
    'end_date': get_parameter_value_from_variable(dag_config, 'end_date', None),
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    'email_on_failure': True,
    'email': 'sachit.rajbhandari@ga.gov.au',
    'ssh_conn_id': get_parameter_value_from_variable(dag_config, 'ssh_conn_id'),
    'aws_conn_id': get_parameter_value_from_variable(dag_config, 'aws_conn_id'),
    'params': {
        's3bucket': get_parameter_value_from_variable(dag_config, 's3bucket'),
        'numdays': get_parameter_value_from_variable(dag_config, 'numdays', '0'),
        'doupdate': get_parameter_value_from_variable(dag_config, 'doupdate', 'no')
    }
}


dag = DAG(
    'nci_s2_upload_s3',
    doc_md=__doc__,
    default_args=default_args,
    catchup=get_parameter_value_from_variable(dag_config, 'catchup', False),
    schedule_interval=get_parameter_value_from_variable(dag_config, 'schedule_interval', None),
    max_active_runs=3,
    default_view='graph',
    tags=['nci', 'sentinel_2'],
)


with dag:
    # Creating working directory
    # '/g/data/v10/work/s2_nbar_rolling_archive/<current_datetime>_<end_date>_<num_days>'
    COMMON = """
            {% set work_dir = '/g/data/v10/work/s2_nbar_rolling_archive/' 
            + execution_date.strftime('%FT%H%M') + '_'+ yesterday_ds +'_' + params.numdays  -%}
            """
    create_nci_work_dir = SSHOperator(
        task_id='create_nci_work_dir',
        command=dedent(COMMON + """
            set -eux
            mkdir -p {{work_dir}}
            echo "{{ ti.xcom_push(key="work_dir", value=work_dir) }}"
        """),
        do_xcom_push=True
    )
    # Uploading s2_to_s3_rolling.py script to NCI
    sftp_s2_to_s3_script = SFTPOperator(
        task_id='sftp_s2_to_s3_script',
        local_filepath=Path(
            Path(configuration.get('core', 'dags_folder')).parent
        ).joinpath("scripts/s2_to_s3_rolling.py").as_posix(),
        remote_filepath="{{ti.xcom_pull(key='work_dir') }}/s2_to_s3_rolling.py",
        operation=SFTPOperation.PUT,
        create_intermediate_dirs=True
    )
    # Execute script to upload sentinel-2 data to s3 bucket
    aws_conn = AwsHook(aws_conn_id=dag.default_args['aws_conn_id'])
    execute_s2_to_s3_script = SSHOperator(
        task_id='execute_s2_to_s3_script',
        command=dedent("""
            cd {{ ti.xcom_pull(key='work_dir') }}

            # echo on and exit on fail
            set -eux

            # Load the latest stable DEA module
            module use /g/data/v10/public/modules/modulefiles
            module load dea

            # Export AWS Access key/secret from Airflow connection module
            export AWS_ACCESS_KEY_ID={{params.aws_conn.access_key}}
            export AWS_SECRET_ACCESS_KEY={{params.aws_conn.secret_key}}

            python3 '{{ ti.xcom_pull(key='work_dir') }}/s2_to_s3_rolling.py' \
                    -n '{{ params.numdays }}' \
                    -d '{{ yesterday_ds }}' \
                    -b '{{ params.s3bucket }}' \
                    -u '{{ params.doupdate }}'
        """),
        remote_host='gadi-dm.nci.org.au',
        params={'aws_conn': aws_conn.get_credentials()},
        timeout=60 * 5
    )
    # Deletes working folder and uploaded script file
    clean_nci_work_dir = SSHOperator(
        task_id='clean_nci_work_dir',
        # Remove work dir after aws s3 sync
        command=dedent("""
            set -eux
            rm -vrf "{{ ti.xcom_pull(key='work_dir') }}"
        """)
    )
    create_nci_work_dir >> sftp_s2_to_s3_script
    sftp_s2_to_s3_script >> execute_s2_to_s3_script
    execute_s2_to_s3_script >> clean_nci_work_dir
