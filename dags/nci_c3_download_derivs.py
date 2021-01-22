"""

Download derivatives from AWS to NCI and index them into the NCI database

"""

from textwrap import dedent

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator


dag = DAG(
    'nci_c3_download_derivs',
    doc_md=__doc__,
    catchup=False,
    tags=['nci', 'landsat_c3'],
    default_view='tree',
)

with dag:


    # Options:
    # 1. Use s5cmd, save output of transferred files, index them.
    #
    # 2. Save inventory from Athena/raw. Save NCI files from DB. Compare

    setup = SSHOperator(task_id='setup',
                        ssh_conn_id='lpgs_gadi',
                        do_xcom_push=False,
                        command=dedent("""
                        mkdir -p /g/data/v10/work/c3_download_derivs/{{ ts_nodash }}

                        """))

    # Sync WOfS directory
    sync_wofs = SSHOperator(task_id="sync_wofs",
                            ssh_conn_id="lpgs_gadi",
                            remote_host="gadi-dm.nci.org.au",
                            do_xcom_push=False,
                            command=dedent("""
cd /g/data/jw04/ga/ga_ls_wo_3
time ~/bin/s5cmd --stat cp --if-size-differ 's3://dea-public-data/derivative/ga_ls_wo_3/*' ." > /g/data/v10/work/c3_download_derivs/{{ts_nodash}}/ga_ls_wo_3.download.log
    """))

    # Sync FC directory
    sync_fc = SSHOperator(task_id="sync_fc",
                            ssh_conn_id="lpgs_gadi",
                            remote_host="gadi-dm.nci.org.au",
                            do_xcom_push=False,
                            command="""""")


    index_wofs = SSHOperator()


    index_fc = SSHOperator()

    sync_wofs >> index_wofs
    sync_fc >> index_fc
