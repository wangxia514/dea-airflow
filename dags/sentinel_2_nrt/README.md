# SQS indexing Workflow

## Background
This workflow is designed to automate the process where new dataset for an ODC product has been created and stored in AWS S3. The application/software this workflow is based on are:

| application/software | repository        |
| -------------------- | ----------------- |
| datacube core (indexing tool) | https://github.com/opendatacube/datacube-index |
| datacube ows         | https://github.com/opendatacube/datacube-ows |
| datacube explorer    | https://github.com/opendatacube/datacube-explorer |


Other known names are:
- ows-data
- k8s-orchestrate

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
