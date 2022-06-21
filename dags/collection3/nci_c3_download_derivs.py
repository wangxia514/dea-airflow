"""

Download derivatives from AWS to NCI and index them into the NCI database

"""

from datetime import datetime
from textwrap import dedent

import pendulum
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator

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
        ssh_conn_id="lpgs_gadi",
        email=["damien.ayers@ga.gov.au"],
        email_on_failure=True,
        email_on_retry=False,
        owner="Damien Ayers",
        retries=3,
    ),
)

products = [
    "ga_ls_fc_3",
    "ga_ls_wo_3",
    "ga_ls_wo_fq_apr_oct_3",
    "ga_ls_wo_fq_nov_mar_3",
    "ga_ls_wo_fq_cyear_3",
    "ga_ls_wo_fq_myear_3",
    "ga_ls5t_nbart_gm_cyear_3",
    "ga_ls7e_nbart_gm_cyear_3",
    "ga_ls8c_nbart_gm_cyear_3",
    "ga_ls_landcover_class_cyear_2",
    "ga_ls_mangrove_cover_cyear_3",
    "ga_ls_tc_pc_cyear_3",
]

with dag:

    for product in products:
        download = SSHOperator(
            task_id=f"download_{product}",
            # Run on the Gadi Data Mover node, it's specifically spec'd for data transfers, and
            # we use s5cmd to transfer using lots of threads to max out the network pipe, and quickly
            # walk both the S3 tree and the Lustre FS tree.
            remote_host="gadi-dm.nci.org.au",
            # There have been random READ failures when performing this download. So retry a few times.
            # Append to the log file so that we don't lose track of any downloaded files.
            command=dedent(
                f"""
                set -eux
                mkdir -p /g/data/v10/work/c3_download_derivs/{{{{ ts_nodash }}}}
                mkdir -p /g/data/jw04/ga/{product}
                cd /g/data/jw04/ga/{product}
                time ~/bin/s5cmd --stat cp --if-size-differ 's3://dea-public-data/derivative/{product}/*' . >> \
                /g/data/v10/work/c3_download_derivs/{{{{ts_nodash}}}}/{product}.download.log
                """
            ),
        )

        index = SSHOperator(
            task_id=f"index_{product}",
            # Keep FC LS7 version 2.5.0 indexing
            # Suspend FC LS8 version 2.5.1 indexing
            command=dedent(
                f"""
                set -eux
                module load dea
                cd /g/data/v10/work/c3_download_derivs/{{{{ts_nodash}}}}

                awk '/odc-metadata.yaml/ {{print "/g/data/jw04/ga/{product}/" $3}}' {product}.download.log  | \
                xargs -P 4 datacube -v dataset add --no-verify-lineage --product {product}
                """
            ),
            # Attempt to index downloaded datasets, even if there were some failures in the download task
            # We want to avoid missing indexing anything, and any gaps will get filled in next time
            # the download runs.
            trigger_rule="all_done",
        )

        download >> index
