"""
Fetch wagl NRT ancillary.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.kubernetes.secret import Secret
from airflow.kubernetes.volume import Volume
from airflow.kubernetes.volume_mount import VolumeMount


NOW = datetime.now()
DOY = int(NOW.strftime("%j"))

S3_TO_RDS_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/geoscienceaustralia/s3-to-rds:0.1.2"


def sync(*args):
    return "aws s3 sync --only-show-errors " + " ".join(args)


def brdf_doys(doy):
    def clip(doy):
        if doy < 1:
            return 1
        if doy > 361:
            return 361
        return doy

    if (doy - 1 / 8).is_integer():
        doys = {doy}
    else:
        doys = {
            clip(((doy // 8) - 1) * 8 + 1),
            clip((doy // 8) * 8 + 1),
            clip(((doy // 8) + 1) * 8 + 1),
        }

    return {str(d).zfill(3) for d in doys}


SYNC_JOBS = [
    "date",
    "echo synching ozone",
    sync("s3://ga-sentinel/ancillary/lookup_tables/ozone/", "/ancillary/ozone"),
    "echo synching dsm",
    sync("s3://ga-sentinel/ancillary/elevation/tc_aus_3sec/", "/ancillary/dsm"),
    "echo synching elevation",
    sync(
        "s3://ga-sentinel/ancillary/elevation/world_1deg/",
        "/ancillary/elevation/world_1deg",
    ),
    "echo synching aerosol",
    sync(
        '--exclude "*" --include "aerosol.h5"',
        "s3://ga-sentinel/ancillary/aerosol/AATSR/2.0/",
        "/ancillary/aerosol",
    ),
    "echo synching invariant height",
    sync("s3://dea-dev-bucket/s2-wagl-nrt/invariant/", "/ancillary/invariant"),
    "echo synching land sea rasters",
    sync(
        '--exclude "*" --include Land_Sea_Rasters.tar.z',
        "s3://dea-dev-bucket/s2-wagl-nrt/",
        "/ancillary",
    ),
    "echo extracting land sea rasters",
    "tar xvf /ancillary/Land_Sea_Rasters.tar.z -C /ancillary/",
    "chown -R root:10015 /ancillary/Land_Sea_Rasters/",
    "echo removing existing water vapour",
    "mkdir -p /ancillary/water_vapour/",
    "find /ancillary/water_vapour/ -type f -exec rm {} \;",
    "echo synching water vapour",
    *[
        sync(
            f'--exclude "*" --include "*{year}*"',
            "s3://ga-sentinel/ancillary/water_vapour",
            "/ancillary/water_vapour",
        )
        # if first week of year, fetch last year as well
        for year in [NOW.year]
        + ([NOW.year - 1] if NOW.month == 1 and NOW.day < 7 else [])
    ],
    "echo removing existing brdf",
    "mkdir -p /ancillary/brdf-jl/",
    "find /ancillary/brdf-jl/ -type f -exec rm {} \;",
    "echo synching brdf",
    *[
        sync(
            f"",
            f"s3://ga-sentinel/ancillary/BRDF/brdf-jl/data/{doy}/",
            f"/ancillary/brdf-jl/{doy}/",
        )
        for doy in brdf_doys(DOY)
    ],
    "find /ancillary/ -type f",
    # this is needed because we want the wagl_nrt user to have write access
    "find /ancillary/ -type d | xargs chmod g+w",
    "date",
]

affinity = {
    "nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [
                {
                    "matchExpressions": [
                        {
                            "key": "nodetype",
                            "operator": "In",
                            "values": [
                                "spot",
                            ],
                        }
                    ]
                }
            ]
        }
    }
}


tolerations = [
    {"key": "dedicated", "operator": "Equal", "value": "wagl", "effect": "NoSchedule"}
]

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


pipeline = DAG(
    "k8s_wagl_nrt_ancillary",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Sentinel-2 NRT fetch ancillary",
    concurrency=1,
    max_active_runs=1,
    catchup=False,
    params={},
    schedule_interval="5 0 * * *",
    tags=["k8s", "dea", "psc", "wagl", "nrt"],
)

with pipeline:
    START = DummyOperator(task_id="start")

    SYNC = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        annotations={"iam.amazonaws.com/role": "svc-dea-dev-eks-wagl-nrt"},
        cmds=["bash", "-c", " &&\n".join(SYNC_JOBS)],
        image_pull_policy="Always",
        name="sync_ancillaries",
        task_id="sync_ancillaries",
        get_logs=True,
        startup_timeout_seconds=300,
        affinity=affinity,
        tolerations=tolerations,
        volumes=[ancillary_volume],
        volume_mounts=[ancillary_volume_mount],
        labels={
            "runner": "airflow",
            "product": "Sentinel-2",
            "app": "nrt",
            "stage": "sync-ancillaries",
        },
        is_delete_operator_pod=True,
    )

    END = DummyOperator(task_id="end")

    START >> SYNC >> END
