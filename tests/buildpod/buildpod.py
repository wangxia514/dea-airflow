from dea_utils.update_explorer_summaries import explorer_refresh_operator
from airflow.kubernetes.pod_generator import PodGenerator

# from airflow.kubernetes import pod_generator
from kubernetes.client import models as k8s

test_obj = explorer_refresh_operator("TEST_POD")


BASE_CONTAINER_NAME = "base"


pod = k8s.V1Pod(
    api_version="v1",
    kind="Pod",
    metadata=k8s.V1ObjectMeta(
        namespace=test_obj.namespace,
        labels=test_obj.labels,
        name=test_obj.name,
        annotations=test_obj.annotations,
    ),
    spec=k8s.V1PodSpec(
        node_selector=test_obj.node_selector,
        affinity=test_obj.affinity,
        tolerations=test_obj.tolerations,
        init_containers=test_obj.init_containers,
        containers=[
            k8s.V1Container(
                image=test_obj.image,
                name=BASE_CONTAINER_NAME,
                command=test_obj.cmds,
                ports=test_obj.ports,
                image_pull_policy=test_obj.image_pull_policy,
                resources=test_obj.k8s_resources,
                volume_mounts=test_obj.volume_mounts,
                args=test_obj.arguments,
                env=test_obj.env_vars,
                env_from=test_obj.env_from,
            )
        ],
        image_pull_secrets=test_obj.image_pull_secrets,
        service_account_name=test_obj.service_account_name,
        host_network=test_obj.hostnetwork,
        security_context=test_obj.security_context,
        dns_policy=test_obj.dnspolicy,
        scheduler_name=test_obj.schedulername,
        restart_policy="Never",
        priority_class_name=test_obj.priority_class_name,
        volumes=test_obj.volumes,
    ),
)


pod_template = k8s.V1Pod(metadata=k8s.V1ObjectMeta(name="name"))

pod = PodGenerator.reconcile_pods(pod_template, pod)

print(pod)
assert test_obj.labels == {}
