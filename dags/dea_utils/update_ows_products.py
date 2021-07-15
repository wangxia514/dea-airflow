"""
Tool for creating a Kubernetes Pod Operator for Updating Datacube OWS
"""
from collections.abc import Sequence
from textwrap import dedent

import kubernetes.client.models as k8s
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from infra.images import OWS_CONFIG_IMAGE, OWS_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.variables import SECRET_OWS_WRITER_NAME
from webapp_update.update_list import OWS_UPDATE_LIST

# OWS pod specific configuration
OWS_CFG_FOLDER_PATH = "/env/config/ows_refactored"
OWS_CFG_MOUNT_PATH = "/env/config"
OWS_CFG_PATH = OWS_CFG_MOUNT_PATH + "/ows_refactored/ows_root_cfg.py"
OWS_CFG_IMAGEPATH = "/opt/dea-config/prod/services/wms/ows_refactored"
OWS_PYTHON_PATH = "/env/config"
OWS_DATACUBE_CFG = "ows_refactored.ows_root_cfg.ows_cfg"

OWS_SECRETS = [
    Secret("env", "DB_USERNAME", SECRET_OWS_WRITER_NAME, "postgres-username"),
    Secret("env", "DB_PASSWORD", SECRET_OWS_WRITER_NAME, "postgres-password"),
]

# MOUNT OWS_CFG via init_container
# for main container mount
ows_cfg_mount = k8s.V1VolumeMount(
    name="ows-config-volume",
    mount_path=OWS_CFG_MOUNT_PATH,
    sub_path=None,
    read_only=False,
)


ows_cfg_volume = k8s.V1Volume(name="ows-config-volume")


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
    args=["-r", OWS_CFG_IMAGEPATH, OWS_CFG_FOLDER_PATH],
    volume_mounts=[cfg_image_mount],
    name="mount-ows-config",
    working_dir="/opt",
)


def ows_update_operator(products, dag=None):
    """
    Create a Task to update OWS Products and Extents

    OWS Updates are partially configured with environment variables, pass in the `dag` to include
    default environment variables as well.

    """
    if isinstance(products, Sequence) and not isinstance(products, str):
        products = " ".join(products)
    # append ows specific env_vars to default env_vars
    ows_env_vars = {
        "WMS_CONFIG_PATH": OWS_CFG_PATH,
        "DATACUBE_OWS_CFG": OWS_DATACUBE_CFG,
        "PYTHONPATH": OWS_PYTHON_PATH,
    }
    if dag:
        env_vars = dag.default_args.get("env_vars", {}).update(ows_env_vars)
    else:
        env_vars = {}.update(ows_env_vars)

    OWS_BASH_COMMAND = [
        "bash",
        "-c",
        dedent(
            f"""
            datacube-ows-update --version
            datacube-ows-update --views
            for product in {products}; do
                if [ $product == "--all" ]; then
                    datacube-ows-update
                else
                    datacube-ows-update $product
                fi
            done;
        """
        ),
    ]

    return KubernetesPodOperator(
        namespace="processing",
        image=OWS_IMAGE,
        arguments=OWS_BASH_COMMAND,
        secrets=OWS_SECRETS,
        labels={"step": "ows-update-range"},
        name="ows-update-range",
        task_id="ows-update-range",
        get_logs=True,
        volumes=[ows_cfg_volume],
        volume_mounts=[ows_cfg_mount],
        init_containers=[config_container],
        is_delete_operator_pod=False,
        affinity=ONDEMAND_NODE_AFFINITY,
        params=dict(default_products=OWS_UPDATE_LIST),
    )
