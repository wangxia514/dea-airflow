# ARD pipeline workflow

Currently we only have Sentinel-2 NRT pipeline.

# DAGs

## `k8s_wagl_nrt`
The main DAG that runs the ARD processing.

## `k8s_wagl_nrt_ancillary`
Copies ancillary datasets daily to a support EFS filesystem.

## `k8s_wagl_nrt_filter`
Filters level-1 granules for Australian ones only.
