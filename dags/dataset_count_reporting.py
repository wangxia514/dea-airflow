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
import psycopg2
import requests
from airflow import DAG
from airflow.contrib.hooks.aws_athena_hook import AWSAthenaHook
from airflow.contrib.hooks.ssh_hook import SSHHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.hooks.postgres_hook import PostgresHook
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

default_args = {
    'owner': 'Damien Ayers',
    'start_date': days_ago(2),
    'retry_delay': timedelta(minutes=5)
}

LOG = logging.getLogger(__name__)


class PostgresSSHHook(PostgresHook):
    """

    """

    def __init__(self, ssh_hook, *args, **kwargs):
        super(PostgresSSHHook, self).__init__(*args, **kwargs)
        self.ssh_hook = ssh_hook
        self.tunnel = None

    def get_conn(self):
        conn_id = getattr(self, self.conn_name_attr)
        conn = self.get_connection(conn_id)

        if self.tunnel is None:
            self.tunnel = self.ssh_hook.get_tunnel(remote_port=conn.port, remote_host=conn.host)

            self.tunnel.start()

        LOG.info(f"Connected SSH Tunnel: {self.tunnel}")
        # Airflow conflates dbname and schema, even though they are very different in PG

        conn_args = dict(
            host='localhost',
            user=conn.login,
            password=conn.password,
            dbname=self.schema or conn.schema,
            port=self.tunnel.local_bind_port)
        raw_cursor = conn.extra_dejson.get('cursor', False)
        if raw_cursor:
            conn_args['cursor_factory'] = self._get_cursor(raw_cursor)
        # check for ssl parameters in conn.extra
        for arg_name, arg_val in conn.extra_dejson.items():
            if arg_name in ['sslmode', 'sslcert', 'sslkey',
                            'sslrootcert', 'sslcrl', 'application_name',
                            'keepalives_idle']:
                conn_args[arg_name] = arg_val

        # It's important to wrap this connection in a try/finally block, otherwise
        # we can cause a deadlock with the SSHTunnel
        conn = psycopg2.connect(**conn_args)
        return conn

    def close(self):
        self.tunnel.stop()
        self.tunnel = None


dag = DAG(
    'collection_3_dataset_count_reporting',
    default_args=default_args,
    schedule_interval=timedelta(days=1)
)


def retrieve_explorer_counts(explorer_storage_csv_url='https://explorer.dea.ga.gov.au/audit/storage.csv'):
    with requests.get(explorer_storage_csv_url, stream=True) as r:
        lines = (line.decode('utf-8') for line in r.iter_lines())
        next(lines)  # Skip the header

        product_counts = {
            product: count
            for product, count, *rest in csv.reader(lines)
        }
    return product_counts


s


class SQLTemplatedPythonOperator(PythonOperator):
    template_ext = ('.sql',)


def record_pg_datasets_count(ssh_conn_id, postgres_conn_id, templates_dict, *args, **kwargs):
    ssh_hook = SSHHook(ssh_conn_id=ssh_conn_id)
    src_db_hook = PostgresSSHHook(ssh_hook=ssh_hook,
                                  postgres_conn_id=postgres_conn_id)

    records = src_db_hook.get_records(templates_dict['query'])

    dest_db_hook = PostgresHook(postgres_conn_id='aws-db')
    dest_db_hook.insert_rows(table='dataset_counts', rows=records)


def record_lustre_datasets_count(ssh_conn_id, postgres_conn_id):
    ssh_hook = SSHHook(ssh_conn_id)
    conn = ssh_hook.get_conn()
    stdin, stdout, stderr = conn.exec_command('fd -e odc-metadata.yaml /g/data/xu18/ga/ga_ls8c_ard_3 | wc -l')

with dag:
    # Count number of dataset files on NCI
    t1 = SSHOperator(
        task_id="task1",
        command='fd -e odc-metadata.yaml /g/data/xu18/ga/ga_ls8c_ard_3 | wc -l',
        ssh_conn_id='lpgs_gadi')

    SQLTemplatedPythonOperator(
        templates_dict={'query': 'sql/datasets_report.sql'},
        params={
            'ssh_conn_id': 'lpgs_gadi',
            'pg_hook_id': 'nci_dea_prod'
        },
        python_callable=record_pg_datasets_count,
        provide_context=True,
    )
    put_into_postgres = PythonOperator(
        task_id="save_qstat_to_postgres",
        python_callable=my_python_callable
    )

    AWSAthenaHook(
        task_id='count_s3_datasets',
        aws_conn_id='aws_default',

    )
