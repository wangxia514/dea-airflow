"""
WAGL NRT fetch ancillary.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.kubernetes.volume import Volume
from airflow.kubernetes.volume_mount import VolumeMount
from airflow.operators.dummy_operator import DummyOperator


S3_TO_RDS_IMAGE = "geoscienceaustralia/s3-to-rds:0.1.1-unstable.26.g5ffb384"

SYNC_CMD = "aws s3 sync --only-show-errors"
SYNC_JOB = f"""
date &&
echo synching ozone &&
{SYNC_CMD} s3://ga-sentinel/ancillary/lookup_tables/ozone/ /ancillary/ozone &&
echo synching dsm &&
{SYNC_CMD} s3://ga-sentinel/ancillary/elevation/tc_aus_3sec/ /ancillary/dsm &&
echo synching elevation &&
{SYNC_CMD} s3://ga-sentinel/ancillary/elevation/world_1deg/ /ancillary/elevation/world_1deg &&
echo synching aerosol &&
{SYNC_CMD} --exclude "*" --include "aerosol.h5" \
        s3://ga-sentinel/ancillary/aerosol/AATSR/2.0/ /ancillary/aerosol &&
echo synching invariant height &&
{SYNC_CMD} s3://dea-dev-bucket/s2-wagl-nrt/invariant/ /ancillary/invariant &&
echo synching land sea rasters &&
{SYNC_CMD} --exclude "*" --include Land_Sea_Rasters.tar.z \
        s3://dea-dev-bucket/s2-wagl-nrt/ /ancillary &&
echo extracting land sea rasters &&
tar -xvf /ancillary/Land_Sea_Rasters.tar.z -C /ancillary/ &&
find /ancillary/ -type f
date
"""

default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 28),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=30),
    "secrets": [Secret("env", None, "wagl-nrt-aws-creds")],
}


pipeline = DAG(
    "k8s_wagl_nrt_ancillary",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Sentinel-2 NRT fetch ancillary",
    concurrency=1,
    max_active_runs=1,
    catchup=False,
    params={},
    schedule_interval=None,
    tags=["k8s", "dea", "psc", "wagl", "nrt"],
)

ancillary_volume_mount = VolumeMount(
    name="wagl-nrt-ancillary-volume",
    mount_path="/ancillary",
    sub_path=None,
    read_only=False,
)

ancillary_volume = Volume(
    name="wagl-nrt-ancillary-volume",
    configs={"persistentVolumeClaim": {"claimName": "wagl-nrt-ancillary-volume"}},
)

with pipeline:
    START = DummyOperator(task_id="start")

    SYNC = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        annotations={"iam.amazonaws.com/role": "svc-dea-dev-eks-wagl-nrt"},
        cmds=["bash", "-c", SYNC_JOB],
        image_pull_policy="Always",
        name="sync_ancillaries",
        task_id="sync_ancillaries",
        get_logs=True,
        # TODO: affinity=affinity,
        volumes=[ancillary_volume],
        volume_mounts=[ancillary_volume_mount],
        is_delete_operator_pod=True,
    )

    END = DummyOperator(task_id="end")

    START >> SYNC >> END
