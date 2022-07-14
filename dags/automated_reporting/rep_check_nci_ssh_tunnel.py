# -*- coding: utf-8 -*-

"""
check nci conn dat
"""
from airflow import DAG
from plugins.ssh_postgres_plugin.operators.ssh_postgres_operator import SSHPostgresOperator
from datetime import datetime
from airflow.operators.dummy_operator import DummyOperator

default_args = {
    'start_date': datetime(2018, 1, 1, 0, 0),
    'email': ['ramkumar.ramagopalan@ga.gov.au'],
    'email_on_failure': True,
    'email_on_retry': False
}

dag = DAG(
    'test_ssh_tunnel',
    schedule_interval=None,
    default_args=default_args,
    catchup=False
)

kick_off_dag = DummyOperator(
    task_id='kick_off_dag',
    dag=dag
)

sql = "select count(*) from agdc.dataset_type"

with dag:
    test = SSHPostgresOperator(task_id='check_for_tunnel',
                               postgres_conn_id='lpgs_pg',
                               ssh_conn_id='lpgs_gadi',
                               sql=sql,
                               create_tunnel=True)
    kick_off_dag >> test
