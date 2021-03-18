"""
# Count Collection 3 Datasets in Different Environments

Products
- ga_ls5t_ard_3
- ga_ls7e_ard_3
- ga_ls8c_ard_3
- ga_ls_wo_3
- ga_ls_fc_3

Environments
- NCI Filesystem (THREDDS/gdata)
- S3
- NCI Explorer
- Sandbox Explorer
- OWS-Dev Explorer
- OWS-Prod Explorer

Decisions:
- Store record files from multiple places into S3
- From there, insert into Dashboard Postgres
"""
import logging
from datetime import timedelta

import psycopg2
from airflow import DAG
from airflow import secrets
from airflow.contrib.hooks.ssh_hook import SSHHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'Damien Ayers',
    'start_date': days_ago(2),
    'retry_delay': timedelta(minutes=5)
}


LOG = logging.getLogger(__name__)


def exec_pg_ssh_query(postgres_conn_id, ssh_conn_id, query, query_vars=None, **context):
    """
    Execute a PostgreSQL query over an SSH Tunnel

    Uses credentials from Airflow Connections.
    """
    # We can't use PostgresHook here because our TCP port is going to be dynamic,
    # because we are connecting through an SSH Tunnel
    (pg_secret,) = secrets.get_connections(postgres_conn_id)

    ssh_conn = SSHHook(ssh_conn_id=ssh_conn_id)
    tunnel = ssh_conn.get_tunnel(remote_port=pg_secret.port, remote_host=pg_secret.host)

    results = None
    tunnel.start()
    with tunnel:
        LOG.info(f"Connected SSH Tunnel: {tunnel}")
        # Airflow conflates dbname and schema, even though they are very different in PG
        conn_str = (
            f"host=localhost user={pg_secret.login} dbname={pg_secret.schema} "
            f"port={tunnel.local_bind_port} password={pg_secret.password}"
        )
        # It's important to wrap this connection in a try/finally block, otherwise
        # we can cause a deadlock with the SSHTunnel
        conn = psycopg2.connect(conn_str)
        try:
            LOG.info(f"Connected to Postgres: {conn}")

            cur = conn.cursor()
            cur.execute(query, query_vars)
            results = cur.fetchall()

            cur.close()
        finally:
            conn.close()

    return results


dag = DAG(
    'collection_3_dataset_count_reporting',
    default_args=default_args,
    schedule_interval=timedelta(days=1)
)


with dag:
    t1 = SSHOperator(
        task_id="task1",
        command='qstat -x -f -F json',
        ssh_conn_id='lpgs_gadi')

    example_bash_task = BashOperator(
        task_id='example_bash_task',
        bash_command='echo {{ task_instance.xcom_pull(task_ids="get_files") }}',
    )

    put_into_postgres = PythonOperator(
        task_id="save_qstat_to_postgres",
        python_callable=my_python_callable
    )

