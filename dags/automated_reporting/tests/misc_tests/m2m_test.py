"""
Test M2M Api Tasks
"""
# pylint: skip-file

import os
import sys
import logging
import configparser
from datetime import datetime as dt

from automated_reporting.tasks import usgs_insert_hg_l0, usgs_aquisitions

AR_FOLDER = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

config = configparser.ConfigParser()
config.read(os.path.join(AR_FOLDER, "tests", ".env"))

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(handler)

##########################

product_ids = ["landsat_etm_c2_l1", "landsat_ot_c2_l1"]


def main():
    """Run the tasks"""

    acquisitions = usgs_aquisitions.task(
        product_ids=product_ids,
        data_interval_end=dt.now(),
        m2m_credentials=dict(config["usgs_m2m"]),
        aux_data_path=os.path.join(AR_FOLDER, "aux_data"),
    )

    usgs_insert_hg_l0.task(
        data_interval_end=dt.now(),
        rep_conn=dict(config["reporting_db"]),
        acquisitions=acquisitions,
    )


if __name__ == "__main__":
    main()
