# -*- coding: utf-8 -*-

"""
check nci conn dat
"""
from airflow import DAG
from datetime import datetime
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.hooks.postgres_hook import PostgresHook

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
    catchup=False,
    tags=["reporting_dev"]
)

kick_off_dag = DummyOperator(
    task_id='kick_off_dag',
    dag=dag
)


def select_from_tunnel_db():
    """ ssh tunnel and db connection """
    # Open SSH tunnel
    ssh_hook = SSHHook(ssh_conn_id='lpgs_gadi', keepalive_interval=60)
    tunnel = ssh_hook.get_tunnel(5432, remote_host='dea-db.nci.org.au', local_port=5432)
    tunnel.start()

    # Connect to DB and run query
    conn = PostgresHook.get_connection('lpgs_pg')
    conn.host = "localhost"
    pg_hook = PostgresHook(connection=conn)
    pg_cursor = pg_hook.get_conn().cursor()
    pg_cursor.execute('select count(*) from agdc.dataset_type;')
    select_val = pg_cursor.fetchall()
    print(select_val)
    return select_val


with dag:
    python_operator = PythonOperator(
        task_id='test_tunnel_conn',
        python_callable=select_from_tunnel_db,
        dag=dag
    )
    kick_off_dag >> python_operator
