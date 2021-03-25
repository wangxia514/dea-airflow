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

import requests
from airflow import DAG
from airflow.contrib.hooks.aws_athena_hook import AWSAthenaHook
from airflow.contrib.hooks.ssh_hook import SSHHook
from airflow.hooks.postgres_hook import PostgresHook
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago

from dea_airflow_common.postgres_ssh_hook import PostgresSSHHook

default_args = {
    'owner': 'Damien Ayers',
    'start_date': days_ago(2),
    'retry_delay': timedelta(minutes=5)
}

LOG = logging.getLogger(__name__)

DEST_POSTGRES_CONN_ID = 'aws-db'

dag = DAG(
    'collection_3_dataset_count_reporting',
    default_args=default_args,
    schedule_interval=timedelta(days=1),
    catchup=False,
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


def record_pg_datasets_count(ssh_conn_id,
                             postgres_conn_id,
                             templates_dict,
                             *args, **kwargs):
    ssh_hook = SSHHook(ssh_conn_id=ssh_conn_id)
    src_db_hook = PostgresSSHHook(ssh_hook=ssh_hook,
                                  postgres_conn_id=postgres_conn_id)

    records = src_db_hook.get_records(templates_dict['query'])

    dest_db_hook = PostgresHook(postgres_conn_id=DEST_POSTGRES_CONN_ID)
    dest_db_hook.insert_rows(table='dataset_counts', rows=records)


def record_lustre_datasets_count(ssh_conn_id,
                                 postgres_conn_id,
                                 product_name,
                                 location):
    ssh_hook = SSHHook(ssh_conn_id)
    conn = ssh_hook.get_conn()
    stdin, stdout, stderr = conn.exec_command(f'fd -e odc-metadata.yaml {location} | wc -l')


with dag:
    DEST_POSTGRES = 'aws-db'
    PRODUCTS = {
        'ga_ls8c_ard_3': '/g/data/xu18/ga/ga_ls8c_ard_3',
        'ga_ls7e_ard_3': '/g/data/xu18/ga/ga_ls7e_ard_3',
        'ga_ls5t_ard_3': '/g/data/xu18/ga/ga_ls5t_ard_3',
        'ga_ls_fc_3': '/g/data/jw04/ga/ga_ls_fc_3/',
        'ga_ls_wo_3': '/g/data/jw04/ga/ga_ls_wo_3/',
    }
    # Count number of dataset files on NCI
    for prod, location in PRODUCTS.items():
        t1 = PythonOperator(
            task_id=f"record_nci_fs_count_{prod}",
            python_callable=record_lustre_datasets_count,
            params=dict(
                ssh_conn_id='lpgs_gadi',
                product_name=prod,
                location=location
            )
        )

    record_nci_db_counts = PythonOperator(
        task_id='record_nci_db_counts',
        templates_dict={'query': 'sql/datasets_report.sql'},
        templates_exts=['.sql'],
        params={
            'ssh_conn_id': 'lpgs_gadi',
            'pg_hook_id': 'nci_dea_prod'
        },
        python_callable=record_pg_datasets_count,
        provide_context=True,
    )

    EXPLORER_INSTANCES = {
        'prod': 'https://explorer-nci.dea.ga.gov.au/audit/storage.csv',
        'dev': 'https://explorer-nci.dev.dea.ga.gov.au/audit/storage.csv'
    }
    for instance, storage_csv_url in EXPLORER_INSTANCES.items():
        PythonOperator(
            task_id=f'record_explorer_{instance}',
            python_callable=retrieve_explorer_counts,
            params=dict(
                instance_name=instance,
                explorer_storage_csv_url=storage_csv_url
            )
        )


def record_athena_stats():
    athena_hook = AWSAthenaHook(
        aws_conn_id='aws_default',

    )
