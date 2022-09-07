"""
# qa audit check: 07/09/2022

"""
from airflow.models import Variable

# HNRS ((Hydrometric Networks and Remote Sensing) DB config
# Note: this DB run within same DB cluster as odc, so reuse
# the odc db hostname and port.
HNRS_DB_DATABASE = Variable.get("hnrs_db_database", default_var="hnrs_dc")
SECRET_HNRS_DC_ADMIN_NAME = Variable.get(
    "db_hnrs_dc_admin_secret", default_var="hnrs-dc-admin"
)

SECRET_HNRS_DC_WRITER_NAME = Variable.get(
    "db_hnrs_dc_writer_secret", default_var="hnrs-dc-writer"
)

WATERBODIES_DEV_USER_SECRET = Variable.get(
    "waterbodies_dev_user_secret", default_var="waterbodies-dev-user-creds"
)  # qa

WIT_DEV_USER_SECRET = Variable.get(
    "wit_dev_user_secret", default_var="wit-dev-user-creds"
)

WATERBODIES_DB_WRITER_SECRET = Variable.get(
    "waterbodies_writer", default_var="waterbodies-writer"
)
