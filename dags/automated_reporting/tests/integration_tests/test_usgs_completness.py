"""
Integration Tests for S2 Completness
"""
# pylint: skip-file
import sys
import logging
import dateutil.parser as parser
from datetime import timedelta
import unittest
from unittest.mock import patch, MagicMock

from automated_reporting.tasks import usgs_completeness

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(handler)


class CompletenessTests_USGS_L1(unittest.TestCase):

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
    task_instance = MagicMock()
    task_instance.xcom_pull = MagicMock(return_value=xcom_acquisitions)

    completeness_kwargs = {
        "execution_date": parser.isoparse("2021-05-20T20:30:00.000000+00:00"),
        "rep_conn": "rep_conn",
        "task_instance": task_instance,
        "aux_data_path": "some_data_path",
    }
    aoi_return = ["107_080", "107_081", "107_082", "107_083", "107_084", "107_085"]

    stac_metadata = [
        [
            [
                "LC81070852021138LGN00",
                "107",
                "085",
                "RT",
                "02",
                parser.isoparse("2021-05-18T01:35:22.689111Z"),
            ],
            [
                "LC81070842021138LGN00",
                "107",
                "084",
                "RT",
                "02",
                parser.isoparse("2021-05-18T01:34:58.734530Z"),
            ],
            [
                "LC81070832021138LGN00",
                "107",
                "083",
                "RT",
                "02",
                parser.isoparse("2021-05-18T01:34:34.779951Z"),
            ],
            [
                "LC81070822021138LGN00",
                "107",
                "082",
                "RT",
                "02",
                parser.isoparse("2021-05-18T01:34:10.833843Z"),
            ],
            [
                "LC81070812021138LGN00",
                "107",
                "081",
                "RT",
                "02",
                parser.isoparse("2021-05-18T01:33:46.879265Z"),
            ],
        ],
        [
            [
                "LE71070852021138LGN00",
                "107",
                "085",
                "RT",
                "02",
                parser.isoparse("2021-05-18T01:45:22.689111Z"),
            ],
            [
                "LE71070852021139LGN00",
                "107",
                "085",
                "RT",
                "02",
                parser.isoparse("2021-05-18T01:34:58.734530Z"),
            ],
        ],
    ]
    s3_listing = [
        [
            ("LC81070852021138LGN00",),
            ("LC81070842021138LGN00",),
            ("LC81070832021138LGN00",),
            ("LC81070822021138LGN00",),
        ],
        [("LE71070852021138LGN00",)],
    ]

    @patch("automated_reporting.tasks.usgs_completeness.gen_sql_completeness_path_row")
    @patch("automated_reporting.tasks.usgs_completeness.gen_sql_completeness")
    @patch(
        "automated_reporting.tasks.usgs_completeness.get_s3_listing",
        side_effect=s3_listing,
    )
    @patch(
        "automated_reporting.tasks.usgs_completeness.get_stac_metadata",
        side_effect=stac_metadata,
    )
    @patch("automated_reporting.tasks.usgs_completeness.gen_m2m_api_inserts")
    @patch(
        "automated_reporting.utilities.helpers.get_aoi_list", return_value=aoi_return
    )
    def test_usgs_l1(
        self,
        mock_aoi,
        mock_m2m_inserts,
        mock_stac_metadata,
        mock_s3_listing,
        mock_gen_completeness,
        mock_gen_completeness_path_row,
    ):

        currency = usgs_completeness.task(**self.completeness_kwargs)

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

        # test get_stac_metadata call
        get_stac_call_1 = mock_stac_metadata.call_args_list[0][0]
        self.assertEqual(
            get_stac_call_1[2],
            parser.isoparse("2021-05-20T20:30:00.000000Z") - timedelta(days=30),
        )
        self.assertEqual(
            get_stac_call_1[3], parser.isoparse("2021-05-20T20:30:00.000000Z")
        )
        print(get_stac_call_1)
