"""
# Experimental Test DAG

A bit of a playground for new development.
"""
from airflow import DAG
from datetime import datetime

from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.email_operator import EmailOperator

from operators.ssh_operators import ShortCircuitSSHOperator, TemplateToSFTPOperator

default_args = {
    "owner": "Damien Ayers",
    "depends_on_past": False,
    "start_date": datetime(2020, 2, 1),
    "email": ["damien.ayers@ga.gov.au", "damien@omad.net"],
    "email_on_failure": True,
}

dag = DAG(
    "testdag",
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    template_searchpath="/home/omad/airflow/dags/templates/",
)

with dag:

    foo = SSHOperator(
        ssh_conn_id="lpgs_gadi",
        task_id="foo",
        remote_host="gadi-dm.nci.org.au",
        command="env",
    )

    failing_task = ShortCircuitSSHOperator(
        task_id="failing_task", ssh_conn_id="lpgs_gadi", command="false"
    )
    should_be_skipped = DummyOperator(task_id="should_be_skipped")
    passing_task = ShortCircuitSSHOperator(
        task_id="passing_task", ssh_conn_id="lpgs_gadi", command="true"
    )
    should_be_run = DummyOperator(task_id="should_be_run")
    failing_task >> should_be_skipped
    passing_task >> should_be_run

    send_email = EmailOperator(
        task_id="send_email",
        to="damien@omad.net",
        subject="New dea/unstable Module",
        html_content="Successfully built new dea/unstable module on the NCI",
        mime_charset="utf-8",
    )
    # foo = BashOperator(
    #     task_id='foo',
    #     bash_command="echo Input is: {{ dag_run.conf.hello }}"
    #
    # )
    upload_template_var = TemplateToSFTPOperator(
        task_id="upload_template_var",
        ssh_conn_id="omad_localhost",
        remote_filepath="/home/omad/{{ ds }}test.txt",
        file_contents="testtemplate.jinja2",
        create_intermediate_dirs=False,
        file_mode=0o644,
    )
