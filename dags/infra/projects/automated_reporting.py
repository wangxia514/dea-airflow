"""
# Automated reporting dags infrastracture provided
# variables
"""
from airflow.models import Variable

# automated-reporting
COP_API_REP_CREDS = "copernicus_api_password"  # not in use

AWS_STATS_SECRET = Variable.get(
    "aws_stats_secret", default_var="aws-stats"
)  # not used anywhere


SARA_HISTORY_SECRET = Variable.get(
    "sara_history_secret", default_var="sara-history"
)  # not used anywhere
ARCHIE_SECRET = Variable.get("archie_secret", default_var="archie")  # not used anywhere
UPTIME_ROBOT_SECRET = Variable.get(
    "uptime_robot_secret", default_var="uptime-robot"
)  # not used anywhere

REPORTING_ASB_ANALYTICS_API_SECRET = Variable.get(
    "reporting_asb_analytics_api_secret", default_var="reporting-asb-analytics-api"
)  # not used anywhere

REPORTING_SCIHUB_API_SECRET = Variable.get(
    "reporting_scihub_api_secret", default_var="reporting-scihub-api"
)  # not used anywhere
