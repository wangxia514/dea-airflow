"""
This script conducts unit tests on the rep_nrt_usgs_completeness.py
"""

import unittest
import pathlib
import os
import logging

from airflow.models import DagBag

from automated_reporting.rep_nrt_usgs_completeness import (
    completeness_comparison_all,
    collect_stac_api_results,
    landsat_path_row,
    filter_aoi,
)
import usgs_completeness_sample_data as sample_data

logger = logging.getLogger("airflow.task")

## Structure and Integration tests
class TestUSGSCompletenessDAGStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_folder = pathlib.Path(__file__).parent.parent.parent.absolute()
        dag_folder = os.path.join(base_folder, "dags", "automated_reporting")
        cls.dagbag = DagBag(dag_folder=dag_folder)

    def test_dag_loaded(self):
        dag = self.dagbag.get_dag(dag_id="nrt_completeness_usgs_nrt_l1")
        self.assertDictEqual(self.dagbag.import_errors, {})
        self.assertIsNotNone(dag)
        self.assertEqual(len(dag.tasks), 2)

    def test_task(self):
        dag = self.dagbag.get_dag(dag_id="nrt_completeness_usgs_nrt_l1")
        self.assertTrue(dag.has_task("run_main"))


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
                "2021-05-16T22:20:39.348258Z",
            ],
            [
                "LC80682002021136LGN00",
                "068",
                "200",
                "RT",
                "02",
                "2021-05-16T22:20:15.448746Z",
            ],
        ]
        s3Listing = ["LC80682012021136LGN00", "LC80682002021136LGN00"]

        file_path = "dags/automated_reporting/aux_data/landsat_l1_path_row_list.txt"
        wrsPathRowList = landsat_path_row(file_path)

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
        assert latestSatAcq == "2021-05-16T22:20:39.348258Z"

    def test_completeness_comparison_all_ga_one_missing(self):
        stacApi = [
            [
                "LC80682012021136LGN00",
                "068",
                "201",
                "RT",
                "02",
                "2021-05-16T22:20:39.348258Z",
            ],
            [
                "LC80682002021136LGN00",
                "068",
                "200",
                "RT",
                "02",
                "2021-05-16T22:20:15.448746Z",
            ],
        ]
        s3Listing = ["LC80682012021136LGN00"]

        file_path = "dags/automated_reporting/aux_data/landsat_l1_path_row_list.txt"
        wrsPathRowList = landsat_path_row(file_path)

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
            ["LC80682002021136LGN00", "068_200", "2021-05-16T22:20:15.448746Z"]
        ]
        assert usgsCount == 2
        assert gaCount == 1
        assert latestSatAcq == "2021-05-16T22:20:39.348258Z"

    def test_completeness_comparison_all_usgs_one_missing(self):
        stacApi = [
            [
                "LC80682012021136LGN00",
                "068",
                "201",
                "RT",
                "02",
                "2021-05-16T22:20:39.348258Z",
            ]
        ]
        s3Listing = ["LC80682012021136LGN00", "LC80682002021136LGN00"]

        file_path = "dags/automated_reporting/aux_data/landsat_l1_path_row_list.txt"
        wrsPathRowList = landsat_path_row(file_path)

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
        assert latestSatAcq == "2021-05-16T22:20:39.348258Z"

    def test_aoi_filtering(self):
        file_path = "dags/automated_reporting/aux_data/landsat_l1_path_row_list.txt"
        wrsPathRowList = landsat_path_row(file_path)
        stacApi = sample_data.stacApi
        s3List = sample_data.landsat8List

        filteredStacApiData, filteredS3List = filter_aoi(
            wrsPathRowList, stacApi, s3List
        )

        assert len(filteredStacApiData) == 415
        assert len(filteredS3List) == 1156

    def test_completeness_comparison_wrs_path_row(self):
        stacApi = sample_data.stacApi
        s3Listing = sample_data.landsat8List

        file_path = "dags/automated_reporting/aux_data/landsat_l1_path_row_list.txt"
        wrsPathRowList = landsat_path_row(file_path)

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
        assert latestSatAcq == "2021-05-18T01:35:22.689111Z"
        assert gaCountValidation == 415
        assert usgsCountValidation == 415

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
