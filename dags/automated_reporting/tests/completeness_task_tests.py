"""
Test M2M Api Tasks
"""
# pylint: skip-file

import os
import sys
import logging
import configparser
from datetime import datetime as dt

from automated_reporting.tasks import s2_completeness

AR_FOLDER = os.path.dirname(os.path.dirname(__file__))

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


def main():
    """Run the tasks"""

    completeness_kwargs = {
        "days": 1,
        "execution_date": dt.now(),
        "rep_conn": config["reporting_db"],
        "odc_conn": config["odc_db"],
        "copernicus_api_credentials": config["copernicus_credentials"],
        "aux_data_path": os.path.join(AR_FOLDER, "aux_data"),
    }

    completeness_kwargs_ard = {
        "s2a": {
            "id": "s2a",
            "odc_code": "s2a_nrt_granule",
            "rep_code": "ga_s2a_msi_ard_c3",
        },
        "s2b": {
            "id": "s2b",
            "odc_code": "s2b_nrt_granule",
            "rep_code": "ga_s2b_msi_ard_c3",
        },
    }
    completeness_kwargs_ard.update(completeness_kwargs)
    s2_completeness.task_ard(**completeness_kwargs_ard)

    completeness_kwargs_ard_prov = {
        "s2a": {
            "id": "s2a",
            "odc_code": "ga_s2am_ard_provisional_3",
            "rep_code": "ga_s2am_ard_provisional_3",
        },
        "s2b": {
            "id": "s2b",
            "odc_code": "ga_s2bm_ard_provisional_3",
            "rep_code": "ga_s2bm_ard_provisional_3",
        },
    }
    completeness_kwargs_ard_prov.update(completeness_kwargs)
    s2_completeness.task_ard(**completeness_kwargs_ard_prov)

    completeness_kwargs_wo = {
        "upstream": ["s2a_nrt_granule", "s2b_nrt_granule"],
        "target": "ga_s2_wo_3",
    }
    completeness_kwargs_wo.update(completeness_kwargs)
    s2_completeness.task_derivative(**completeness_kwargs_wo)

    completeness_kwargs_ba = {
        "upstream": ["ga_s2am_ard_provisional_3", "ga_s2bm_ard_provisional_3"],
        "target": "ga_s2_ba_provisional_3",
    }
    completeness_kwargs_ba.update(completeness_kwargs)
    s2_completeness.task_derivative(**completeness_kwargs_ba)


if __name__ == "__main__":
    main()
