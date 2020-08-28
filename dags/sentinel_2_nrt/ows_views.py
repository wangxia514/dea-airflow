"""
# Sentinel-2_nrt ows update
"""
from airflow import DAG
from airflow.kubernetes.volume import Volume
from airflow.kubernetes.volume_mount import VolumeMount
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator

from textwrap import dedent

import kubernetes.client.models as k8s

from images import OWS_CFG_IMAGEPATH, OWS_CONFIG_IMAGE, OWS_IMAGE
from env_cfg import OWS_CFG_PATH, OWS_CFG_MOUNT_PATH


UPDATE_EXTENT_PRODUCTS = "s2_nrt_granule_nbar_t"

# MOUNT OWS_CFG via init_container
# for main container mount
ows_cfg_mount = VolumeMount(
    "ows-config-volume", mount_path=OWS_CFG_MOUNT_PATH, sub_path=None, read_only=False
)


ows_cfg_volume_config = {}

ows_cfg_volume = Volume(name="ows-config-volume", configs=ows_cfg_volume_config)


# for init container mount
cfg_image_mount = k8s.V1VolumeMount(
    mount_path=OWS_CFG_MOUNT_PATH,
    name="ows-config-volume",
    sub_path=None,
    read_only=False,
)

config_container = k8s.V1Container(
    image=OWS_CONFIG_IMAGE,
    command=["cp"],
    args=[OWS_CFG_IMAGEPATH, OWS_CFG_PATH],
    volume_mounts=[cfg_image_mount],
    name="mount-ows-config",
    working_dir="/opt",
)

OWS_BASH_COMMAND = [
    "bash",
    "-c",
    dedent(
        """
        datacube-ows-update --views;
        for product in %s; do
            datacube-ows-update $product;
        done;
    """
    )
    % (UPDATE_EXTENT_PRODUCTS),
]

OWS_UPDATE_EXTENTS = KubernetesPodOperator(
    namespace="processing",
    image=OWS_IMAGE,
    arguments=OWS_BASH_COMMAND,
    labels={"step": "ows-mv"},
    name="ows-update-extents",
    task_id="ows-update-extents",
    get_logs=True,
    volumes=[ows_cfg_volume],
    volume_mounts=[ows_cfg_mount],
    init_containers=[config_container],
    is_delete_operator_pod=True,
)
