# Collection 3 indexing
This folder contains DAGs for indexing Collection 3 data into the `odc` database in the dea-sandbox-eks cluster. The dags for indexing into the `sandbox` database are managed seperately.

## Products

Currently there are DAGs for indexing the following products:

#### Baseline
- `ga_ls5t_ard_3`
- `ga_ls7e_ard_3`
- `ga_ls8c_ard_3`

#### Derivative
- `ga_ls_wo_3`
- `ga_ls_fc_3`

## DAGs

There are currently 4 DAGs in total: 2 for indexing the baseline products and 2 for indexing the derivative products. The `k8s_index_*_odc` DAGs index from SQS queues, and the `k8s_index_*_backlog_odc` DAGs performing bulk indexing directly from S3.

## AWS Setup

Currently there is 1 IAM role used for the DAGs in this folder. The following SQS queues are used:

- 1 x index queue for baseline products
- 1 x archive queue for baseline products
- 1 x queue each for derivative products

