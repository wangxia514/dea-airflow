"""
# Rebuild `dea/unstable` module on the NCI

"""
from datetime import datetime, timedelta

import pendulum
from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.email_operator import EmailOperator

local_tz = pendulum.timezone("Australia/Canberra")

default_args = {
    'owner': 'Damien Ayers',
    'start_date': datetime(2020, 3, 12, tzinfo=local_tz),
    'retries': 0,
    'timeout': 1200,  # For running SSH Commands
    'email_on_failure': True,
    'email_on_retry': False,
    'email': 'damien.ayers@ga.gov.au',
}

dag = DAG(
    'nci_build_dea_unstable_module',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    tags=['nci'],
)

with dag:
    build_dea_unstable_module = SSHOperator(
        task_id='build_dea_unstable_module',
        ssh_conn_id='lpgs_gadi',
        command="""
        set -eux
        cd ~/dea-orchestration/
        git reset --hard
        git pull
        cd ~/dea-orchestration/nci_environment
        git status
        module load python3/3.7.4
        pip3 install --user pyyaml jinja2
        
        rm -rf /g/data/v10/public/modules/dea/unstable/
        ./build_environment_module.py dea_unstable/modulespec.yaml
        """,
    )

    # post_to_slack = SlackAPIPostOperator(
    #     task_id='post_to_slack',
    #     slack_conn_id='',
    #     channel='#dea-beginners',
    #     username='airflow-bot',
    #     text='Successfully built new dea/unstable module on the NCI',
    #     icon_url='',
    #
    # )

#    send_email = EmailOperator(
#        task_id='send_email',
#        to=['damien.ayers@ga.gov.au'],
#        subject='New dea/unstable Module',
#        html_content='Successfully built new dea/unstable module on the NCI',
#        mime_charset='utf-8',
#    )

#    build_dea_unstable_module >> [send_email]
