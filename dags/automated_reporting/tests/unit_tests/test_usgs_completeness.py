"""
This script conducts unit tests on the rep_nrt_usgs_completeness.py
"""
# pylint: skip-file

import os
import unittest
import logging
from datetime import datetime as dt, timezone

from automated_reporting.tasks.usgs_completeness import (
    completeness_comparison_all,
    filter_aoi,
)
from automated_reporting.utilities.stac_api import collect_stac_api_results
from automated_reporting.tests.data import (
    usgs_completeness_sample_data as sample_data,
)
from automated_reporting.utilities import helpers

logger = logging.getLogger("airflow.task")
AR_FOLDER = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


class TestUSGSCompletenessDagUnits(unittest.TestCase):

    logger = logging.getLogger("airflow.task")

    def setup(self):
        """
        Get config and setup logging
        :return:
        """
        self.logger = logging.getLogger("airflow.task")

    def test_completeness_comparison_all_no_missing(self):
        stacApi = [
            [
                "LC80682012021136LGN00",
                "068",
                "201",
                "RT",
                "02",
                dt(2021, 5, 16, 22, 20, 39, 348258, tzinfo=timezone.utc),
            ],
            [
                "LC80682002021136LGN00",
                "068",
                "200",
                "RT",
                "02",
                dt(2021, 5, 16, 22, 20, 15, 448746, tzinfo=timezone.utc),
            ],
        ]
        s3Listing = ["LC80682012021136LGN00", "LC80682002021136LGN00"]
        wrsPathRowList = helpers.get_aoi_list(
            os.path.join(AR_FOLDER, "aux_data"), "landsat_l1_path_row_list.txt"
        )

        (
            successCounter,
            missingCounter,
            missingMatrix,
            usgsCount,
            gaCount,
            latestSatAcq,
            pathRowCounterMatrix,
        ) = completeness_comparison_all(stacApi, s3Listing, wrsPathRowList, self.logger)

        assert successCounter == 2
        assert missingCounter == 0
        assert missingMatrix == []
        assert usgsCount == 2
        assert gaCount == 2
        assert latestSatAcq == dt(2021, 5, 16, 22, 20, 39, 348258, tzinfo=timezone.utc)

    def test_completeness_comparison_all_ga_one_missing(self):
        stacApi = [
            [
                "LC80682012021136LGN00",
                "068",
                "201",
                "RT",
                "02",
                dt(2021, 5, 16, 22, 20, 39, 348258, tzinfo=timezone.utc),
            ],
            [
                "LC80682002021136LGN00",
                "068",
                "200",
                "RT",
                "02",
                dt(2021, 5, 16, 22, 20, 15, 448746, tzinfo=timezone.utc),
            ],
        ]
        s3Listing = ["LC80682012021136LGN00"]
        wrsPathRowList = helpers.get_aoi_list(
            os.path.join(AR_FOLDER, "aux_data"), "landsat_l1_path_row_list.txt"
        )

        (
            successCounter,
            missingCounter,
            missingMatrix,
            usgsCount,
            gaCount,
            latestSatAcq,
            pathRowCounterMatrix,
        ) = completeness_comparison_all(stacApi, s3Listing, wrsPathRowList, self.logger)

        assert successCounter == 1
        assert missingCounter == 1
        assert missingMatrix == [
            [
                "LC80682002021136LGN00",
                "068_200",
                dt(2021, 5, 16, 22, 20, 15, 448746, tzinfo=timezone.utc),
            ]
        ]
        assert usgsCount == 2
        assert gaCount == 1
        assert latestSatAcq == dt(2021, 5, 16, 22, 20, 39, 348258, tzinfo=timezone.utc)

    def test_completeness_comparison_all_usgs_one_missing(self):
        stacApi = [
            [
                "LC80682012021136LGN00",
                "068",
                "201",
                "RT",
                "02",
                dt(2021, 5, 16, 22, 20, 39, 348258, tzinfo=timezone.utc),
            ]
        ]
        s3Listing = ["LC80682012021136LGN00", "LC80682002021136LGN00"]
        wrsPathRowList = helpers.get_aoi_list(
            os.path.join(AR_FOLDER, "aux_data"), "landsat_l1_path_row_list.txt"
        )

        (
            successCounter,
            missingCounter,
            missingMatrix,
            usgsCount,
            gaCount,
            latestSatAcq,
            pathRowCounterMatrix,
        ) = completeness_comparison_all(stacApi, s3Listing, wrsPathRowList, self.logger)

        assert successCounter == 1
        assert missingCounter == 0
        assert missingMatrix == []
        assert usgsCount == 1
        assert gaCount == 2
        assert latestSatAcq == dt(2021, 5, 16, 22, 20, 39, 348258, tzinfo=timezone.utc)

    def test_aoi_filtering(self):
        wrsPathRowList = helpers.get_aoi_list(
            os.path.join(AR_FOLDER, "aux_data"), "landsat_l1_path_row_list.txt"
        )
        stacApi = sample_data.stacApi
        s3List = sample_data.landsat8List

        filteredStacApiData, filteredS3List = filter_aoi(
            wrsPathRowList, stacApi, s3List
        )

        assert len(filteredStacApiData) == 415
        assert len(filteredS3List) == 1156

    def test_completeness_comparison_wrs_path_row(self):
        stacApi = []
        for row in sample_data.stacApi:
            row[5] = dt.strptime(row[5], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=timezone.utc
            )
            stacApi.append(row)

        s3Listing = sample_data.landsat8List

        wrsPathRowList = helpers.get_aoi_list(
            os.path.join(AR_FOLDER, "aux_data"), "landsat_l1_path_row_list.txt"
        )

        filteredStacApiData, filteredS3List = filter_aoi(
            wrsPathRowList, stacApi, s3Listing
        )

        (
            successCounter,
            missingCounter,
            missingMatrix,
            usgsCount,
            gaCount,
            latestSatAcq,
            pathRowCounterMatrix,
        ) = completeness_comparison_all(
            filteredStacApiData, filteredS3List, wrsPathRowList, self.logger
        )

        gaCountValidation = 0
        usgsCountValidation = 0

        for row in pathRowCounterMatrix:
            gaCountValidation += row[2]
            usgsCountValidation += row[1]

        assert gaCount == 1156
        assert usgsCount == 415
        assert missingCounter == 0
        assert missingMatrix == []
        assert latestSatAcq == dt(2021, 5, 18, 1, 35, 22, 689111, tzinfo=timezone.utc)
        assert gaCountValidation == 415
        assert usgsCountValidation == 415

    def test_completeness_comparison_wrs_path_row_matrix_has_missing_scenes(self):

        stacApi = [
            [
                "LC80682012021136LGN00",
                "068",
                "201",
                "RT",
                "02",
                dt(2021, 5, 16, 22, 20, 39, 348258, tzinfo=timezone.utc),
            ],
            [
                "LC80682002021136LGN00",
                "068",
                "200",
                "RT",
                "02",
                dt(2021, 5, 16, 22, 20, 15, 448746, tzinfo=timezone.utc),
            ],
            [
                "MISSING_LC80682002021136LGN00",
                "068",
                "200",
                "RT",
                "02",
                dt(2021, 5, 16, 22, 20, 15, 448746, tzinfo=timezone.utc),
            ],
        ]
        s3Listing = ["LC80682012021136LGN00", "LC80682002021136LGN00"]
        wrsPathRowList = ["068_201", "068_200"]
        (
            successCounter,
            missingCounter,
            missingMatrix,
            usgsCount,
            gaCount,
            latestSatAcq,
            pathRowCounterMatrix,
        ) = completeness_comparison_all(stacApi, s3Listing, wrsPathRowList, self.logger)

        pr_068_200 = [row for row in pathRowCounterMatrix if row[0] == "068_200"][0]
        pr_068_201 = [row for row in pathRowCounterMatrix if row[0] == "068_201"][0]

        self.assertEqual(len(pr_068_200[3]), 1)
        self.assertEqual(len(pr_068_201[3]), 0)
        self.assertEqual(pr_068_200[3][0], "MISSING_LC80682002021136LGN00")

    def test_completeness_comparison_wrs_path_row_matrix_has_latest_sat_acq_time(self):

        stacApi = [
            [
                "LC80682012021136LGN00",
                "068",
                "201",
                "RT",
                "02",
                dt(2021, 5, 16, 22, 20, 39, 348258, tzinfo=timezone.utc),
            ],
            [
                "LC80682002021136LGN00_1",
                "068",
                "200",
                "RT",
                "02",
                dt(2021, 5, 16, 22, 20, 15, 448746, tzinfo=timezone.utc),
            ],
            [
                "LC80682002021136LGN00_2",
                "068",
                "200",
                "RT",
                "02",
                dt(2021, 5, 16, 23, 20, 15, 448746, tzinfo=timezone.utc),
            ],
        ]
        s3Listing = [
            "LC80682012021136LGN00",
            "LC80682002021136LGN00_1",
            "LC80682002021136LGN00_2",
        ]
        wrsPathRowList = ["068_201", "068_200"]
        (
            successCounter,
            missingCounter,
            missingMatrix,
            usgsCount,
            gaCount,
            latestSatAcq,
            pathRowCounterMatrix,
        ) = completeness_comparison_all(stacApi, s3Listing, wrsPathRowList, self.logger)

        pr_068_200 = [row for row in pathRowCounterMatrix if row[0] == "068_200"][0]
        pr_068_201 = [row for row in pathRowCounterMatrix if row[0] == "068_201"][0]

        self.assertEqual(
            max(pr_068_200[4]), dt(2021, 5, 16, 23, 20, 15, 448746, tzinfo=timezone.utc)
        )

    def test_collect_stac_api_results(self):
        output = {
            "type": "FeatureCollection",
            "meta": {"page": 1, "limit": 10, "found": 1, "returned": 1},
            "features": [
                {
                    "properties": {
                        "datetime": "2021-05-16T22:20:39.348258Z",
                        "view:sun_azimuth": -36.2906826,
                        "view:sun_elevation": -37.3497175,
                        "platform": "LANDSAT_8",
                        "eo:instrument": ["OLI", "TIRS"],
                        "view:off_nadir": 0,
                        "landsat:cloud_cover_land": -1,
                        "landsat:wrs_type": "2",
                        "landsat:wrs_path": "068",
                        "landsat:wrs_row": "201",
                        "landsat:scene_id": "LC80682012021136LGN00",
                        "landsat:collection_category": "RT",
                        "landsat:collection_number": "02",
                    },
                }
            ],
        }

        stacApiMatrix = collect_stac_api_results(output)

        assert stacApiMatrix == [
            [
                "LC80682012021136LGN00",
                "068",
                "201",
                "RT",
                "02",
                "2021-05-16T22:20:39.348258Z",
            ]
        ]


if __name__ == "__main__":
    unittest.main(verbosity=1)
