"""
MODTRAN6 image test.
"""
from datetime import datetime

import kubernetes.client.models as k8s
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

MOD6_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/dev/mod6:test-20210311"

ancillary_volume_mount = k8s.V1VolumeMount(
    name="wagl-nrt-ancillary-volume",
    mount_path="/modtran6",
    sub_path=None,
    read_only=False,
)

ancillary_volume = k8s.V1Volume(
    name="wagl-nrt-ancillary-volume",
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
        claim_name="wagl-nrt-ancillary-volume"
    )
)

default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2021, 3, 3),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    "k8s_wagl_modtran_test",
    doc_md=__doc__,
    default_args=default_args,
    description="modtran6 image test",
    catchup=False,
    params={},
    concurrency=1,
    max_active_runs=1,
    schedule_interval=None,
    tags=["k8s", "dea", "psc", "dev", "wagl"],
)

with dag:
    START = DummyOperator(task_id="start")
    JOB = KubernetesPodOperator(
        task_id="run_one",
        namespace="processing",
        name="mod6-test",
        image_pull_policy="Always",
        image=MOD6_IMAGE,
        volumes=[ancillary_volume],
        volume_mounts=[ancillary_volume_mount],
        env_vars={"MODTRAN_DATA": "/modtran6/MODTRAN6.0/DATA"},
        secrets=[Secret("env", None, "mod6-key")],
        startup_timeout_seconds=600,
        labels={
            "runner": "airflow",
            "app": "CaRSA",
        },
        is_delete_operator_pod=True,
    )
    END = DummyOperator(task_id="end")

    START >> JOB >> END
