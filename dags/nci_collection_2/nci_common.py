"""
Common configuration for Collection 2 Processing on the NCI
"""
from datetime import datetime

import pendulum

local_tz = pendulum.timezone("Australia/Canberra")

c2_start_date = datetime(2020, 3, 12, tzinfo=local_tz)

# “At 01:00 on Tuesday, Thursday and Saturday.”
# https://crontab.guru/#0_1_*_*_2,4,6
c2_schedule_interval = "0 1 * * 2,4,6"

c2_default_args = {
    "owner": "Damien Ayers",
    "depends_on_past": False,
    "start_date": c2_start_date,
    "email": [
        "damien.ayers@ga.gov.au",
        "david.gavin@ga.gov.au",
    ],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": 5 * 60,
    "ssh_conn_id": "lpgs_gadi",
    "params": {
        "project": "v10",
        "queue": "normal",
        "module": "dea",
        "year": "2021",
        "queue_size": "10000",
    },
}
HOURS = 60 * 60
MINUTES = 60
DAYS = HOURS * 24
