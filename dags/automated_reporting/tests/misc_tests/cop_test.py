"""
Test M2M Api Tasks
"""
# pylint: skip-file

import os
import sys
import logging
import configparser
from datetime import datetime as dt

from automated_reporting.utilities import copernicus_api

AR_FOLDER = os.path.dirname(os.path.dirname(__file__))

config = configparser.ConfigParser()
config.read(os.path.join(AR_FOLDER, ".env"))

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(handler)

##########################


def main():
    """Run the tasks"""

    acquisitions = copernicus_api.query(
        execution_date=dt.now(),
        days=3,
        copernicus_api_creds=dict(config["copernicus_credentials"]),
    )
    pass


if __name__ == "__main__":
    main()
