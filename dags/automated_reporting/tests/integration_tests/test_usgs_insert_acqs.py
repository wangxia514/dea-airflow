"""
Integration Tests for USGS M2M Inserts
"""
# pylint: skip-file
import sys
import logging
import dateutil.parser as parser
import unittest
from unittest.mock import patch

from automated_reporting.tasks import usgs_insert_acqs

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(handler)


class TestUSGSInsertAcqs(unittest.TestCase):

    xcom_acquisitions = [
        {
            "id": "LC81070852021138LGN00",
            "acq_time": "2021-05-18T01:35:22.689111+00:00",
            "l1_time": "2021-05-18T03:35:22.689111+00:00",
            "display_id": "LC8_L1GT_103065_20210919_20210919_02_RT",
            "cloud_cover": "76.00",
            "collect_cat": "RT",
            "collect_num": 2,
            "wrs2": "107_085",
            "platform": "ls8",
        },
        {
            "id": "LE71070852021138LGN00",
            "acq_time": "2021-05-18T01:45:22.689111+00:00",
            "l1_time": "2021-05-18T03:45:22.689111+00:00",
            "display_id": "LE07_L1GT_103065_20210919_20210919_02_RT",
            "cloud_cover": "76.00",
            "collect_cat": "RT",
            "collect_num": 2,
            "wrs2": "107_085",
            "platform": "ls7",
        },
    ]

    completeness_kwargs = {
        "rep_conn": "rep_conn",
        "acquisitions": xcom_acquisitions,
    }

    @patch("automated_reporting.tasks.usgs_insert_acqs.gen_m2m_api_inserts")
    def test_usgs_insert_acqs(self, mock_m2m_inserts):

        usgs_insert_acqs.task(**self.completeness_kwargs)

        # test m2m inserts call
        m2m_inserts = mock_m2m_inserts.call_args[0][1]
        self.assertEqual(len(m2m_inserts), 2)
        self.assertEqual(m2m_inserts[0][0], "LC81070852021138LGN00")
        self.assertEqual(
            parser.isoparse(m2m_inserts[0][5]),
            parser.isoparse("2021-05-18T01:35:22.689111+00:00"),
        )
        self.assertEqual(m2m_inserts[1][0], "LE71070852021138LGN00")
        self.assertEqual(
            parser.isoparse(m2m_inserts[1][5]),
            parser.isoparse("2021-05-18T01:45:22.689111+00:00"),
        )
