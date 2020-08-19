def pod_mutation_hook(pod):
  pod.annotations['airflow.apache.org/launched-by'] = 'Pin Tests'