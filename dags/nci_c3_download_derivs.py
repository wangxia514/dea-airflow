"""

Download derivatives from AWS to NCI and index them into the NCI database

"""

from textwrap import dedent

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator


dag = DAG(
    'nci_c3_download_derivs',
    mod_md=__doc__,
    catchup=False,
    tags=['nci', 'landsat_c3'],
    default_view='tree',
)

with dag:


    # Options:
    # 1. Use s5cmd, save output of transferred files, index them.
    #
    # 2. Save inventory from Athena/raw. Save NCI files from DB. Compare

    # Sync WOfS directory
    sync_wofs = SSHOperator()

    # Sync FC directory
    sync_fc = SSHOperator()


    index_wofs = SSHOperator()


    index_fc = SSHOperator()
