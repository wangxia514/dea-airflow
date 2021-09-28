"""
Integration Tests for S2 Completness
"""
# pylint: skip-file
import sys
import logging
import dateutil.parser as parser
from datetime import timedelta
import unittest
from unittest.mock import patch
from collections import OrderedDict

from automated_reporting.tasks import usgs_l1_completeness
from automated_reporting.tasks import usgs_ard_completeness

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(handler)


class CompletenessTests_USGS_L1(unittest.TestCase):

    completeness_kwargs = {
        "next_execution_date": parser.isoparse("2021-05-20T20:30:00.000000+00:00"),
        "rep_conn": "rep_conn",
        # "task_instance": task_instance,
        "aux_data_path": "some_data_path",
        "days": 30,
        "product": {
            "s3_code": "L8C2",
            "acq_code": "LC8%",
            "rep_code": "landsat_ot_c2_l1",
        },
    }

    aoi_return = ["107_080", "107_081", "107_082", "107_083", "107_084", "107_085"]

    stac_metadata = [
        OrderedDict(
            {
                "scene_id": "LC81070852021138LGN00",
                "wrs_path": "107",
                "wrs_row": "085",
                "collection_category": "RT",
                "collection_number": "02",
                "sat_acq": parser.isoparse("2021-05-18T01:35:22.689111Z"),
            }
        ),
        OrderedDict(
            {
                "scene_id": "LC81070842021138LGN00",
                "wrs_path": "107",
                "wrs_row": "084",
                "collection_category": "RT",
                "collection_number": "02",
                "sat_acq": parser.isoparse("2021-05-18T01:34:58.734530Z"),
            }
        ),
        OrderedDict(
            {
                "scene_id": "LC81070832021138LGN00",
                "wrs_path": "107",
                "wrs_row": "083",
                "collection_category": "RT",
                "collection_number": "02",
                "sat_acq": parser.isoparse("2021-05-18T01:34:34.779951Z"),
            }
        ),
        OrderedDict(
            {
                "scene_id": "LC81070822021138LGN00",
                "wrs_path": "107",
                "wrs_row": "082",
                "collection_category": "RT",
                "collection_number": "02",
                "sat_acq": parser.isoparse("2021-05-18T01:34:10.833843Z"),
            }
        ),
        OrderedDict(
            {
                "scene_id": "LC81070812021138LGN00",
                "wrs_path": "107",
                "wrs_row": "081",
                "collection_category": "RT",
                "collection_number": "02",
                "sat_acq": parser.isoparse("2021-05-18T01:33:46.879265Z"),
            }
        ),
    ]
    s3_listing = [
        {
            "scene_id": "LC81070852021138LGN00",
            "pipeline": "L8C2",
            "last_updated": parser.isoparse("2021-05-18T03:35:22.689111Z"),
        },
        {
            "scene_id": "LC81070842021138LGN00",
            "pipeline": "L8C2",
            "last_updated": parser.isoparse("2021-05-18T03:34:58.734530Z"),
        },
        {
            "scene_id": "LC81070832021138LGN00",
            "pipeline": "L8C2",
            "last_updated": parser.isoparse("2021-05-18T03:34:34.779951Z"),
        },
        {
            "scene_id": "LC81070822021138LGN00",
            "pipeline": "L8C2",
            "last_updated": parser.isoparse("2021-05-18T03:34:10.833843Z"),
        },
    ]

    @patch(
        "automated_reporting.databases.reporting_db_usgs.get_s3_listing",
        return_value=s3_listing,
    )
    @patch(
        "automated_reporting.databases.reporting_db_usgs.get_m2m_metadata",
        return_value=stac_metadata,
    )
    @patch(
        "automated_reporting.utilities.helpers.get_aoi_list", return_value=aoi_return
    )
    @patch("automated_reporting.databases.reporting_db.insert_completeness")
    def test_usgs_l1(
        self, mock_rep_inserts, mock_aoi, mock_m2m_metadata, mock_s3_listing
    ):

        summary = usgs_l1_completeness.task(**self.completeness_kwargs)

        self.assertEqual(summary["expected"], 5)
        self.assertEqual(summary["missing"], 1)
        self.assertEqual(summary["actual"], 4)
        self.assertEqual(summary["completeness"], 80.0)
        self.assertEqual(
            parser.isoparse(summary["latest_sat_acq_ts"]),
            parser.isoparse("2021-05-18T01:35:22.689111Z"),
        )
        self.assertEqual(
            parser.isoparse(summary["latest_processing_ts"]),
            parser.isoparse("2021-05-18T03:35:22.689111Z"),
        )

        # test get_stac_metadata call
        get_m2m_call = mock_m2m_metadata.call_args_list[0][0]
        self.assertEqual(
            get_m2m_call[2],
            parser.isoparse("2021-05-20T20:30:00.000000Z") - timedelta(days=30),
        )
        self.assertEqual(
            get_m2m_call[3], parser.isoparse("2021-05-20T20:30:00.000000Z")
        )


class CompletenessTests_USGS_ARD(unittest.TestCase):

    completeness_kwargs = {
        "next_execution_date": parser.isoparse("2021-05-20T20:30:00.000000+00:00"),
        "rep_conn": "rep_conn",
        "odc_conn": "odc_conn",
        "product": dict(acq_code="sdfsdf", odc_code="ga_ls8c_ard_provisional_3"),
        "days": 30,
        "aux_data_path": "some_data_path",
    }
    aoi_return = ["107_080", "107_081", "107_082", "107_083", "107_084", "107_085"]

    m2m_metadata = [
        OrderedDict(
            {
                "scene_id": "LC81070852021138LGN00",
                "wrs_path": "107",
                "wrs_row": "085",
                "collection_category": "RT",
                "collection_number": "02",
                "sat_acq": parser.isoparse("2021-05-18T01:35:22.689111Z"),
            }
        ),
        OrderedDict(
            {
                "scene_id": "LC81070842021138LGN00",
                "wrs_path": "107",
                "wrs_row": "084",
                "collection_category": "RT",
                "collection_number": "02",
                "sat_acq": parser.isoparse("2021-05-18T01:34:58.734530Z"),
            }
        ),
    ]
    odc_return_target = [
        {
            "id": "some-uuid",
            "granule_id": "LS_SCENE_ID_01",
            "parent_id": "LC81070852021138LGN00",
            "tile_id": "107085",
            "satellite_acquisition_time": parser.isoparse(
                "2021-05-18T01:35:22.689111Z"
            ),
            "processing_time": parser.isoparse("2021-05-18T03:35:22.689111Z"),
        }
    ]

    @patch(
        "automated_reporting.databases.odc_db.query",
        side_effect=[odc_return_target],
    )
    @patch(
        "automated_reporting.databases.reporting_db_usgs.get_m2m_metadata",
        side_effect=[m2m_metadata],
    )
    @patch(
        "automated_reporting.utilities.helpers.get_aoi_list", return_value=aoi_return
    )
    @patch("automated_reporting.databases.reporting_db.insert_completeness")
    def test_usgs_ard(
        self,
        mock_rep_inserts,
        mock_aoi,
        mock_m2m_metadata,
        mock_odc_query,
    ):

        summary = usgs_ard_completeness.task(**self.completeness_kwargs)

        self.assertEqual(summary["expected"], 2)
        self.assertEqual(summary["missing"], 1)
        self.assertEqual(summary["actual"], 1)
        self.assertEqual(summary["completeness"], 50.0)
        self.assertEqual(
            parser.isoparse(summary["latest_sat_acq_ts"]),
            parser.isoparse("2021-05-18T01:35:22.689111Z"),
        )
        self.assertEqual(
            parser.isoparse(summary["latest_processing_ts"]),
            parser.isoparse("2021-05-18T03:35:22.689111Z"),
        )

        inserts = mock_rep_inserts.call_args_list[0][0][1]
        self.assertEqual(len(inserts), 7)
        self.assertEqual(len(list(filter(lambda x: x[0] == "all_ls", inserts))), 1)
        self.assertEqual(
            len(list(filter(lambda x: x[0] in self.aoi_return, inserts))), 6
        )
        missing = [
            x
            for x in inserts
            if x[0] == "107_084" and x[4] == "ga_ls8c_ard_provisional_3"
        ][0]
        self.assertEqual(missing[8][0][0], "LC81070842021138LGN00")
