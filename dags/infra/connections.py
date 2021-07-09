"""
# connection ids created by terraform
"""

# Automated reporting connections
DB_ODC_READER_CONN = "db_odc_reader"  # qa
DB_REP_WRITER_CONN_DEV = "db_rep_writer_dev"
DB_REP_WRITER_CONN_PROD = "db_rep_writer_prod"
S3_REP_CONN = "s3_bucket_rep"

AWS_SENTINEL_2_ARD_SYNC_CONN = "sentinel_2_ard_sync_user"  # qa

# AWS CONN Alignment
AWS_WAGL_NRT_CONN = "aws_wagl_nrt"  # qa
AWS_DEAD_LETTER_QUEUE_CHECKER_CONN = "aws_dead_letter_sqs_queue_checker"  # qa
