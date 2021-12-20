"""
Test SNS Currency Database reads and writes
"""
# pylint: skip-file

import os
import sys
import logging
import configparser
import dateutil.parser as parser

from automated_reporting.tasks import sns_latency

AR_FOLDER = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

config = configparser.ConfigParser()
config.read(os.path.join(AR_FOLDER, "tests", ".env"))

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.DEBUG)
log.addHandler(handler)

##########################


def main():
    """Run the tasks"""

    sns_latency.task(
        pipeline="S2A_MSIL1C",
        product_id="s2a_l1_nrt",
        data_interval_end=parser.isoparse("2021-09-21T11:45:00.000000+00:00"),
        rep_conn=dict(config["reporting_db"]),
    )


if __name__ == "__main__":
    main()
