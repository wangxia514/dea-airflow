"""
WAGL NRT ancillary sync try 2.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.kubernetes.volume import Volume
from airflow.kubernetes.volume_mount import VolumeMount
from airflow.operators.dummy_operator import DummyOperator


S3_TO_RDS_IMAGE = "geoscienceaustralia/s3-to-rds:0.1.1-unstable.26.g5ffb384"

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
    "k8s_wagl_nrt_ancillary_2",
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
    name="s3-backup-volume", mount_path="/ancillary", sub_path=None, read_only=False
)

ancillary_volume = Volume(
    name="wagl-nrt-ancillary-volume",
    configs={"persistentVolumeClaim": {"claimName": "wagl-nrt-ancillary-volume"}},
)

with pipeline:
    START = DummyOperator(task_id="start")

    COPY = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        annotations={"iam.amazonaws.com/role": "svc-dea-dev-eks-wagl-nrt"},
        cmds=["echo", "Hello", "$AWS_DEFAULT_REGION"],
        image_pull_policy="Always",
        name="sync_ancillaries",
        task_id="sync_ancillaries",
        get_logs=True,
        # TODO: affinity=affinity,
        volumes=[ancillary_volume],
        volume_mounts=[ancillary_volume_mount],
    )

    END = DummyOperator(task_id="end")

    START >> COPY >> END
