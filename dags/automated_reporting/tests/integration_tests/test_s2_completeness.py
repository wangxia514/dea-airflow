"""
Integration Tests for S2 Completness
"""
# pylint: skip-file
import sys
import logging
import dateutil.parser as parser
import unittest
from unittest.mock import patch

from automated_reporting.tasks import s2_completeness

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(handler)


class CompletenessTests_S2_ARD(unittest.TestCase):
    """Run the tasks"""

    completeness_kwargs = {
        "days": 1,
        "next_execution_date": parser.isoparse("2021-09-03T20:30:00.000000+10"),
        "rep_conn": "rep_conn",
        "odc_conn": "odc_conn",
        "copernicus_api_credentials": {},
        "aux_data_path": "some_data_path",
    }
    odc_return = [
        {
            "id": "some-uuid",
            "granule_id": "s2a_granule_id1",
            "parent_id": "s2a_parent_id1",
            "tile_id": "49KGQ",
            "satellite_acquisition_time": parser.isoparse(
                "2021-09-03T02:30:00.000000Z"
            ),
            "processing_time": parser.isoparse("2021-09-03T04:30:00.000000Z"),
        }
    ]
    copernicus_return = [
        {
            "uuid": "some-uuid",
            "granule_id": "s2a_parent_id1",
            "region_id": "49KGQ",
            "sensor": "s2a",
        },
        {
            "uuid": "some-uuid",
            "granule_id": "s2a_parent_id2",
            "region_id": "49KGP",
            "sensor": "s2a",
        },
    ]
    aoi_return = ["49JHN", "49KGP", "49KGQ", "49KGR"]

    @patch(
        "automated_reporting.utilities.helpers.get_aoi_list", return_value=aoi_return
    )
    @patch("automated_reporting.databases.odc_db.query", return_value=odc_return)
    @patch(
        "automated_reporting.utilities.copernicus_api.query",
        return_value=copernicus_return,
    )
    @patch("automated_reporting.databases.reporting_db.insert_completeness")
    def test_s2_ard(
        self, mock_rep_inserts, mock_copernicus_query, mock_odc_query, mock_aoi
    ):
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
        completeness_kwargs_ard.update(self.completeness_kwargs)
        summary = s2_completeness.task_ard(**completeness_kwargs_ard)

        self.assertEqual(mock_odc_query.call_args_list[0][0][1], "s2a_nrt_granule")
        self.assertEqual(mock_odc_query.call_args_list[1][0][1], "s2b_nrt_granule")

        self.assertEqual(summary["s2a"]["expected"], 2)
        self.assertEqual(summary["s2a"]["missing"], 1)
        self.assertEqual(summary["s2a"]["actual"], 1)
        self.assertEqual(summary["s2a"]["completeness"], 50.0)
        self.assertEqual(
            parser.isoparse(summary["s2a"]["latest_sat_acq_ts"]),
            parser.isoparse("2021-09-03T02:30:00.000000Z"),
        )
        self.assertEqual(
            parser.isoparse(summary["s2a"]["latest_processing_ts"]),
            parser.isoparse("2021-09-03T04:30:00.000000Z"),
        )

        self.assertEqual(summary["s2b"]["expected"], 0)
        self.assertEqual(summary["s2b"]["missing"], 0)
        self.assertEqual(summary["s2b"]["actual"], 0)
        self.assertEqual(summary["s2b"]["completeness"], None)
        self.assertEqual(summary["s2b"]["latest_sat_acq_ts"], None)
        self.assertEqual(summary["s2b"]["latest_processing_ts"], None)

        inserts = mock_rep_inserts.call_args_list[0][0][1]
        self.assertEqual(len(inserts), 10)
        self.assertEqual(len(list(filter(lambda x: x[0] == "all_s2", inserts))), 2)
        self.assertEqual(
            len(list(filter(lambda x: x[0] in self.aoi_return, inserts))), 8
        )
        missing = [
            x for x in inserts if x[0] == "49KGP" and x[4] == "ga_s2a_msi_ard_c3"
        ][0]
        self.assertEqual(missing[8][0][0], "s2a_parent_id2")

    @patch(
        "automated_reporting.utilities.helpers.get_aoi_list", return_value=aoi_return
    )
    @patch("automated_reporting.databases.odc_db.query", return_value=odc_return)
    @patch(
        "automated_reporting.utilities.copernicus_api.query",
        return_value=copernicus_return,
    )
    @patch("automated_reporting.databases.reporting_db.insert_completeness")
    def test_s2_ard_prov(
        self, mock_rep_inserts, mock_copernicus_query, mock_odc_query, mock_aoi
    ):
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
        completeness_kwargs_ard_prov.update(self.completeness_kwargs)
        summary = s2_completeness.task_ard(**completeness_kwargs_ard_prov)

        self.assertEqual(
            mock_odc_query.call_args_list[0][0][1], "ga_s2am_ard_provisional_3"
        )
        self.assertEqual(
            mock_odc_query.call_args_list[1][0][1], "ga_s2bm_ard_provisional_3"
        )

        self.assertEqual(summary["s2a"]["expected"], 2)
        self.assertEqual(summary["s2a"]["missing"], 1)
        self.assertEqual(summary["s2a"]["actual"], 1)
        self.assertEqual(summary["s2a"]["completeness"], 50.0)
        self.assertEqual(
            parser.isoparse(summary["s2a"]["latest_sat_acq_ts"]),
            parser.isoparse("2021-09-03T02:30:00.000000Z"),
        )
        self.assertEqual(
            parser.isoparse(summary["s2a"]["latest_processing_ts"]),
            parser.isoparse("2021-09-03T04:30:00.000000Z"),
        )

        self.assertEqual(summary["s2b"]["expected"], 0)
        self.assertEqual(summary["s2b"]["missing"], 0)
        self.assertEqual(summary["s2b"]["actual"], 0)
        self.assertEqual(summary["s2b"]["completeness"], None)
        self.assertEqual(summary["s2b"]["latest_sat_acq_ts"], None)
        self.assertEqual(summary["s2b"]["latest_processing_ts"], None)

        inserts = mock_rep_inserts.call_args_list[0][0][1]
        self.assertEqual(len(inserts), 10)
        self.assertEqual(len(list(filter(lambda x: x[0] == "all_s2", inserts))), 2)
        self.assertEqual(
            len(list(filter(lambda x: x[0] in self.aoi_return, inserts))), 8
        )
        missing = [
            x
            for x in inserts
            if x[0] == "49KGP" and x[4] == "ga_s2am_ard_provisional_3"
        ][0]
        self.assertEqual(missing[8][0][0], "s2a_parent_id2")


class CompletenessTests_S2_Deriv(unittest.TestCase):
    """Run the tasks"""

    completeness_kwargs = {
        "days": 1,
        "next_execution_date": parser.isoparse("2021-09-03T20:30:00.000000+10"),
        "rep_conn": "rep_conn",
        "odc_conn": "odc_conn",
        "copernicus_api_credentials": {},
        "aux_data_path": "some_data_path",
    }
    odc_return_target = [
        {
            "id": "some-uuid",
            "granule_id": "s2a_granule_id1",
            "parent_id": "s2a_parent_id1",
            "tile_id": "49KGQ",
            "satellite_acquisition_time": parser.isoparse(
                "2021-09-03T02:30:00.000000Z"
            ),
            "processing_time": parser.isoparse("2021-09-03T06:30:00.000000Z"),
        }
    ]
    odc_return_upstream1 = [
        {
            "id": "some-uuid",
            "granule_id": "s2a_parent_id1",
            "parent_id": "s2a_parent_id1",
            "tile_id": "49KGQ",
            "satellite_acquisition_time": parser.isoparse(
                "2021-09-03T02:30:00.000000Z"
            ),
            "processing_time": parser.isoparse("2021-09-03T04:30:00.000000Z"),
        }
    ]
    odc_return_upstream2 = [
        {
            "id": "some-uuid",
            "granule_id": "s2b_parent_id2",
            "parent_id": "s2b_parent_id2",
            "tile_id": "49KGP",
            "satellite_acquisition_time": parser.isoparse(
                "2021-09-03T02:30:00.000000Z"
            ),
            "processing_time": parser.isoparse("2021-09-03T04:30:00.000000Z"),
        }
    ]
    aoi_return = ["49JHN", "49KGP", "49KGQ", "49KGR"]

    @patch(
        "automated_reporting.utilities.helpers.get_aoi_list", return_value=aoi_return
    )
    @patch(
        "automated_reporting.databases.odc_db.query",
        side_effect=[odc_return_upstream1, odc_return_upstream2, odc_return_target],
    )
    @patch("automated_reporting.databases.reporting_db.insert_completeness")
    def test_s2_deriv_wo(self, mock_rep_inserts, mock_odc_query, mock_aoi):
        completeness_kwargs_wo = {
            "upstream": ["s2a_nrt_granule", "s2b_nrt_granule"],
            "target": "ga_s2_wo_3",
        }
        completeness_kwargs_wo.update(self.completeness_kwargs)
        summary = s2_completeness.task_derivative(**completeness_kwargs_wo)

        self.assertEqual(mock_odc_query.call_args_list[0][0][1], "s2a_nrt_granule")
        self.assertEqual(mock_odc_query.call_args_list[1][0][1], "s2b_nrt_granule")
        self.assertEqual(mock_odc_query.call_args_list[2][0][1], "ga_s2_wo_3")

        self.assertEqual(summary["ga_s2_wo_3"]["expected"], 2)
        self.assertEqual(summary["ga_s2_wo_3"]["missing"], 1)
        self.assertEqual(summary["ga_s2_wo_3"]["actual"], 1)
        self.assertEqual(summary["ga_s2_wo_3"]["completeness"], 50.0)
        self.assertEqual(
            parser.isoparse(summary["ga_s2_wo_3"]["latest_sat_acq_ts"]),
            parser.isoparse("2021-09-03T02:30:00.000000Z"),
        )
        self.assertEqual(
            parser.isoparse(summary["ga_s2_wo_3"]["latest_processing_ts"]),
            parser.isoparse("2021-09-03T06:30:00.000000Z"),
        )

        inserts = mock_rep_inserts.call_args_list[0][0][1]
        self.assertEqual(len(inserts), 5)
        self.assertEqual(len(list(filter(lambda x: x[0] == "all_s2", inserts))), 1)
        self.assertEqual(
            len(list(filter(lambda x: x[0] in self.aoi_return, inserts))), 4
        )
        missing = [x for x in inserts if x[0] == "49KGP" and x[4] == "ga_s2_wo_3"][0]
        self.assertEqual(missing[8][0][0], "s2b_parent_id2")

    @patch(
        "automated_reporting.utilities.helpers.get_aoi_list", return_value=aoi_return
    )
    @patch(
        "automated_reporting.databases.odc_db.query",
        side_effect=[odc_return_upstream1, odc_return_upstream2, odc_return_target],
    )
    @patch("automated_reporting.databases.reporting_db.insert_completeness")
    def test_s2_deriv_ba_prov(self, mock_rep_inserts, mock_odc_query, mock_aoi):
        completeness_kwargs_ba = {
            "upstream": ["ga_s2am_ard_provisional_3", "ga_s2bm_ard_provisional_3"],
            "target": "ga_s2_ba_provisional_3",
        }
        completeness_kwargs_ba.update(self.completeness_kwargs)
        summary = s2_completeness.task_derivative(**completeness_kwargs_ba)

        self.assertEqual(
            mock_odc_query.call_args_list[0][0][1], "ga_s2am_ard_provisional_3"
        )
        self.assertEqual(
            mock_odc_query.call_args_list[1][0][1], "ga_s2bm_ard_provisional_3"
        )
        self.assertEqual(
            mock_odc_query.call_args_list[2][0][1], "ga_s2_ba_provisional_3"
        )

        self.assertEqual(summary["ga_s2_ba_provisional_3"]["expected"], 2)
        self.assertEqual(summary["ga_s2_ba_provisional_3"]["missing"], 1)
        self.assertEqual(summary["ga_s2_ba_provisional_3"]["actual"], 1)
        self.assertEqual(summary["ga_s2_ba_provisional_3"]["completeness"], 50.0)
        self.assertEqual(
            parser.isoparse(summary["ga_s2_ba_provisional_3"]["latest_sat_acq_ts"]),
            parser.isoparse("2021-09-03T02:30:00.000000Z"),
        )
        self.assertEqual(
            parser.isoparse(summary["ga_s2_ba_provisional_3"]["latest_processing_ts"]),
            parser.isoparse("2021-09-03T06:30:00.000000Z"),
        )

        inserts = mock_rep_inserts.call_args_list[0][0][1]
        self.assertEqual(len(inserts), 5)
        self.assertEqual(len(list(filter(lambda x: x[0] == "all_s2", inserts))), 1)
        self.assertEqual(
            len(list(filter(lambda x: x[0] in self.aoi_return, inserts))), 4
        )
        missing = [
            x for x in inserts if x[0] == "49KGP" and x[4] == "ga_s2_ba_provisional_3"
        ][0]
        self.assertEqual(missing[8][0][0], "s2b_parent_id2")


if __name__ == "__main__":
    unittest.main()
