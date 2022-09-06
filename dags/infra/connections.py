"""
infra provided connids
if commented with qa, it is being setup in helm chart
and not in-application ui or cli.
"""
# AWS CONN Alignment

DB_ODC_READER_CONN = "db_odc_reader" # qa

AWS_NCI_DB_BACKUP_CONN = "aws_nci_db_backup_s3" # qa
AWS_DEA_PUBLIC_DATA_LANDSAT_3_SYNC_CONN = "aws_dea_public_data_landsat_3_sync" # qa
AWS_WAGL_NRT_CONN = "aws_wagl_nrt" # qa

# QA DB CONN
DB_EXPLORER_READ_CONN = "db_explorer_reader" # qa
DB_ODC_WRITER_CONN = "db_odc_writer" # qa
