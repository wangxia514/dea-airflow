from airflow.models import Variable

# dea-access
DEA_ACCESS_RESTO_API_ADMIN_SECRET = Variable.get(
    "dea_access_resto_api_admin_secret", default_var="dea-access-resto-api-admin"
)  # qa
