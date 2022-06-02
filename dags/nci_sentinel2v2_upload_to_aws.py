"""

Upload Sentinel 2 (V2) data from the NCI to AWS

"""

from textwrap import dedent
from datetime import datetime

import pendulum
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook as AwsHook

local_tz = pendulum.timezone("Australia/Canberra")

dag = DAG(
    "nci_sentinel2v2_upload_to_aws",
    doc_md=__doc__,
    catchup=False,
    tags=["nci", "sentinel2"],
    default_view="tree",
    start_date=datetime(2022, 6, 1, tzinfo=local_tz),
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

products = ("ga_s2am_ard_3", "ga_s2bm_ard_3")

with dag:
    aws_hook = AwsHook(aws_conn_id="aws-dea-dev-uploader", client_type="s3")
    for product in products:
        upload = SSHOperator(
            task_id=f"upload_{product}",
            # Run on the Gadi Data Mover node, it's specifically spec'd for data transfers, and
            # we use s5cmd to transfer using lots of threads to max out the network pipe, and quickly
            # walk both the S3 tree and the Lustre FS tree.
            remote_host="gadi-dm.nci.org.au",
            # There have been random READ failures when performing this download. So retry a few times.
            # Append to the log file so that we don't lose track of any downloaded files.
            command=dedent(
                """
                set -eux

                # Export AWS Access key/secret from Airflow connection module
                export AWS_ACCESS_KEY_ID={{aws_creds.access_key}}
                export AWS_SECRET_ACCESS_KEY={{aws_creds.secret_key}}

                cd {{nci_dir}}
                time ~/bin/s5cmd --stat cp --if-source-newer --storage-class INTELLIGENT_TIERING {{product}} s3://dea-public-data-dev/baseline/
                """
            ),
            params={
                "aws_hook": aws_hook,
                "product": product,
                "nci_dir": "/g/data/up71/projects/S2-C3-upgrade-STAC",
            },
        )
