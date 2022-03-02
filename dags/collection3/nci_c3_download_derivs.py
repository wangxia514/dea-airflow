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

products = ["ga_ls_fc_3",

            "ga_ls_wo_3",
            "ga_ls_wo_fq_apr_oct_3",
            "ga_ls_wo_fq_nov_mar_3",
            "ga_ls_wo_fq_cyear_3",
            "ga_ls_wo_fq_myear_3",

            "ga_ls5t_nbart_gm_cyear_3",
            "ga_ls7e_nbart_gm_cyear_3",
            "ga_ls8c_nbart_gm_cyear_3"]

with dag:

    for product in products:
        sync = SSHOperator(
            task_id=f"sync_{product}",
            remote_host="gadi-dm.nci.org.au",
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
            command=dedent(
                f"""
                set -eux
                module load dea
                cd /g/data/v10/work/c3_download_derivs/{{{{ts_nodash}}}}

                awk '/odc-metadata.yaml/ {{print "/g/data/jw04/ga/{product}/" $3}}' {product}.download.log  | \
                xargs -P 4 datacube -v dataset add --no-verify-lineage --product {product}
                """
            ),
        )

        sync >> index
