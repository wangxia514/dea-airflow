from airflow.contrib.kubernetes.pod import Pod

def pod_mutation_hook(pod: Pod):
    extra_labels = {
        "test-label": "True",
    }
    pod.labels.update(extra_labels)