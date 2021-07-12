"""
# Sentinel-2_nrt ows update
"""
from textwrap import dedent

from kubernetes.client import models as k8s
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.kubernetes.volume_mount import VolumeMount
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from infra.images import OWS_CONFIG_IMAGE, OWS_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.pools import DEA_NEWDATA_PROCESSING_POOL
from infra.variables import SECRET_OWS_WRITER_NAME
from subdags.podconfig import (
    OWS_CFG_PATH,
    OWS_CFG_MOUNT_PATH,
    OWS_CFG_IMAGEPATH,
    OWS_DATACUBE_CFG,
    OWS_PYTHON_PATH,
    OWS_CFG_FOLDER_PATH,
)
from webapp_update.update_list import UPDATE_EXTENT_PRODUCTS

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


def ows_update_extent_subdag(
    parent_dag_name: str, child_dag_name: str, args: dict, xcom_task_id: str = None
):
    """[summary]

    Args:
        parent_dag_name (str): [Name of parent dag]
        child_dag_name (str): [Name of this dag for parent dag's reference]
        args (dict): [dag arguments]
        xcom_task_id (str, optional): [If this dag needs to xcom_pull a products value set by a pre-task]. Defaults to None.

    Returns:
        [type]: [subdag for processing]
    """

    if xcom_task_id:
        products = (
            "{{{{ task_instance.xcom_pull(dag_id='{}', task_ids='{}') }}}}".format(
                parent_dag_name, xcom_task_id
            )
        )
    else:
        products = " ".join(UPDATE_EXTENT_PRODUCTS)

    # append ows specific env_vars to args
    ows_env_cfg = {
        "WMS_CONFIG_PATH": OWS_CFG_PATH,
        "DATACUBE_OWS_CFG": OWS_DATACUBE_CFG,
        "PYTHONPATH": OWS_PYTHON_PATH,
    }
    args.setdefault("env_vars", ows_env_cfg).update(ows_env_cfg)

    OWS_BASH_COMMAND = [
        "bash",
        "-c",
        dedent(
            """
            datacube-ows-update --version
            datacube-ows-update --views
            for product in %s; do
                if [ $product == "--all" ]; then
                    datacube-ows-update
                else
                    datacube-ows-update $product
                fi
            done;
        """
        )
        % (products),
    ]

    dag_subdag = DAG(
        dag_id="%s.%s" % (parent_dag_name, child_dag_name),
        default_args=args,
        catchup=False,
        max_active_runs=1,
    )

    KubernetesPodOperator(
        namespace="processing",
        image=OWS_IMAGE,
        arguments=OWS_BASH_COMMAND,
        secrets=OWS_SECRETS,
        labels={"step": "ows-mv"},
        name="ows-update-extents",
        task_id="ows-update-extents",
        get_logs=True,
        volumes=[ows_cfg_volume],
        volume_mounts=[ows_cfg_mount],
        init_containers=[config_container],
        is_delete_operator_pod=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        dag=dag_subdag,
        pool=DEA_NEWDATA_PROCESSING_POOL,
    )

    return dag_subdag


def ows_update_operator(xcom_task_id=None, args={}):
    """
    arg = dag default arg
    """
    if xcom_task_id:
        products = f"{{{{ task_instance.xcom_pull(task_ids='{xcom_task_id}') }}}}"
    else:
        products = " ".join(UPDATE_EXTENT_PRODUCTS)

    # append ows specific env_vars to args
    ows_env_cfg = {
        "WMS_CONFIG_PATH": OWS_CFG_PATH,
        "DATACUBE_OWS_CFG": OWS_DATACUBE_CFG,
        "PYTHONPATH": OWS_PYTHON_PATH,
    }
    args.setdefault("env_vars", ows_env_cfg).update(ows_env_cfg)

    OWS_BASH_COMMAND = [
        "bash",
        "-c",
        dedent(
            """
            datacube-ows-update --version
            datacube-ows-update --views
            for product in %s; do
                if [ $product == "--all" ]; then
                    datacube-ows-update
                else
                    datacube-ows-update $product
                fi
            done;
        """
        )
        % (products),
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
        pool=DEA_NEWDATA_PROCESSING_POOL,
    )
