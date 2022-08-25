import pytest


@pytest.mark.applymanifests("configs", files=["nginx.yaml"])
def test_nginx(kube):
    """An example test against an Nginx deployment."""

    # wait for the manifests loaded by the 'applymanifests' marker
    # to be ready on the cluster
    kube.wait_for_registered(timeout=30)

    deployments = kube.get_deployments()
    nginx_deploy = deployments.get("nginx-deployment")
    assert nginx_deploy is not None

    pods = nginx_deploy.get_pods()
    assert len(pods) == 3, "nginx should deploy with three replicas"

    for pod in pods:
        containers = pod.get_containers()
        assert len(containers) == 1, "nginx pod should have one container"

        resp = pod.http_proxy_get("/")
        assert "<h1>Welcome to nginx!</h1>" in resp.data


@pytest.mark.namespace(create=True, name="processing")
@pytest.mark.applymanifests(
    "configs", files=["lpgs_secret.yaml", "reporting_secret.yaml", "test.json"]
)
def test_testjson(kube):
    """An example test against an Nginx deployment."""

    # wait for the manifests loaded by the 'applymanifests' marker
    # to be ready on the cluster
    pods = kube.get_pods()
    for pod in pods.values():
        pod.wait_until_containers_start(timeout=60)

    pod = pods.get("nci-odc-ga-ls8c-ard-3.a3cb07289f4b45f38aba436d2969b925")
    assert pod is not None

    containers = pod.get_containers()
    assert len(containers) == 1
