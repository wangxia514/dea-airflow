# dea_public_data s3 notification indexing
This is a patterned indexing, to enable indexing datasets from `s3://dea-public-data/` by s3 bucket generated notification for new files arriving into the bucket, simply by adding to the `env_cfg.py` folder.

Criteria:
1. product name must be added to `INDEXING_PRODUCTS` list
2. `s3_uri` path pattern must be added to `PRODUCT_RECORD_PATHS`

## Background
This workflow is designed to automate the process where new dataset for an ODC product has been created and stored in AWS S3. The application/software this workflow is based on are:

| application/software | repository        |
| -------------------- | ----------------- |
| datacube core (indexing tool) | https://github.com/opendatacube/datacube-index |
| datacube ows         | https://github.com/opendatacube/datacube-ows |
| datacube explorer    | https://github.com/opendatacube/datacube-explorer |

### Database setup

| schemas | creator and owner |
| ------- | ----------------- |
| agdc    | https://github.com/opendatacube/datacube-core |
| wms     | https://github.com/opendatacube/datacube-ows |
| cubedash| https://github.com/opendatacube/datacube-explorer |


### Major process components
#### Indexing
create dataset entry in `agdc.dataset` table
##### Streamline indexing
Reads from `AWS SQS queue` for new dataset metadata information and indexes timely.

##### Batch indexing
Scheduled to index directly from `AWS S3 bucket`.

#### Archiving
Update dataset entry in `agdc.dataset` table `archived` column with `datetimestamp`

#### OWS update
Run `datacube-ows-update --views` and `datacube-ows-update` command

#### explorer update
Run `cubedash-gen --no-init-database --refresh-stats --force-refresh` command
