"""

Download derivatives from AWS to NCI and index them into the NCI database

"""

from datetime import datetime
from textwrap import dedent

import pendulum
from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator

local_tz = pendulum.timezone("Australia/Canberra")

dag = DAG(
    "nci_c3_download_derivs",
    doc_md=__doc__,
    catchup=False,
    tags=["nci", "landsat_c3"],
    default_view="tree",
    start_date=datetime(2021, 1, 20, tzinfo=local_tz),
    default_args=dict(
        do_xcom_push=False,
        ssh_conn_id='lpgs_gadi',
        email=['damien.ayers@ga.gov.au'],
        email_on_failure=True,
        owner='Damien Ayers',
    )
)

COMMON = dedent("""
    set -eux
""")

with dag:

    # Need to decide between two options:
    # 1. Use s5cmd, save output of transferred files, index them.
    #
    # 2. Save inventory from Athena/raw. Save NCI files from DB. Compare

    setup = SSHOperator(
        task_id="setup",
        command=dedent(COMMON +
            """
            mkdir -p /g/data/v10/work/c3_download_derivs/{{ ts_nodash }}
            """
        ),
    )

    # Sync WOfS directory using a Gadi Data Mover node
    sync_wofs = SSHOperator(
        task_id="sync_wofs",
        remote_host="gadi-dm.nci.org.au",
        command=dedent(COMMON +
            """
            cd /g/data/jw04/ga/ga_ls_wo_3
            time ~/bin/s5cmd --stat cp --if-size-differ 's3://dea-public-data/derivative/ga_ls_wo_3/*' . > /g/data/v10/work/c3_download_derivs/{{ts_nodash}}/ga_ls_wo_3.download.log
            """
        ),
    )

    # Sync FC directory using a Gadi Data Mover node
    sync_fc = SSHOperator(
        task_id="sync_fc",
        remote_host="gadi-dm.nci.org.au",
        command=dedent(COMMON +
            """
            cd /g/data/jw04/ga/ga_ls_fc_3
            time ~/bin/s5cmd --stat cp --if-size-differ 's3://dea-public-data/derivative/ga_ls_fc_3/*' . > /g/data/v10/work/c3_download_derivs/{{ts_nodash}}/ga_ls_fc_3.download.log
            """
        ),
    )

    index_wofs = SSHOperator(
        task_id="index_wofs",
        command=dedent(COMMON +
            """
            module load dea
            cd /g/data/v10/work/c3_download_derivs/{{ts_nodash}}

            awk '/odc-metadata.yaml/ {print "/g/data/jw04/ga/ga_ls_wo_3/" $0}' ga_ls_wo_3.download.log  | \
            xargs -P 4 datacube -v dataset add --no-verify-lineage --product ga_ls_wo_3
        """
        ),
    )

    index_fc = SSHOperator(
        task_id="index_fc",
        command=dedent(COMMON +
            """
            module load dea
            cd /g/data/v10/work/c3_download_derivs/{{ts_nodash}}

            awk '/odc-metadata.yaml/ {print "/g/data/jw04/ga/ga_ls_fc_3/" $0}' ga_ls_fc_3.download.log  | \
            xargs -P 4 datacube -v dataset add --no-verify-lineage --product ga_ls_fc_3
            """
        ),
    )

    setup >> [sync_fc, sync_wofs]
    sync_wofs >> index_wofs
    sync_fc >> index_fc
