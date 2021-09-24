# pylint: skip-file
import unittest
from datetime import datetime as dt, timedelta as td, timezone as tz

from automated_reporting.utilities.completeness import (
    filter_datasets_to_region,
    get_expected_ids_missing_in_actual,
    get_datasets_in_expected_and_actual,
    calculate_metric_for_region,
    calculate_metrics_for_all_regions,
    calculate_summary_stats,
    Actual,
    Expected,
)


# Unit Tests
class TestCompletenessUnit(unittest.TestCase):

    BT = dt(2021, 4, 21, 2, 15, 23, 345, tzinfo=tz.utc)
    AOI_LIST = ["54DFT", "55DCF", "55KHG"]
    ACTUAL_PRODUCTS = [
        Actual(
            **{
                "dataset_id": "GRANULE_ID_1",
                "parent_id": "PARENT_GRANULE_ID_1",
                "region_id": "54DFT",
                "processing_dt": BT,
                "center_dt": BT - td(hours=6),
            }
        ),
        Actual(
            **{
                "dataset_id": "GRANULE_ID_2",
                "parent_id": "PARENT_GRANULE_ID_2",
                "region_id": "54DFT",
                "processing_dt": BT - td(hours=24),
                "center_dt": BT - td(hours=28),
            }
        ),
        Actual(
            **{
                "dataset_id": "GRANULE_ID_5",
                "parent_id": "PARENT_GRANULE_ID_5",
                "region_id": "54DFT",
                "processing_dt": BT + td(hours=48),
                "center_dt": BT + td(hours=43),
            }
        ),  # tile in region, but not in expected (date error)
        Actual(
            **{
                "dataset_id": "GRANULE_ID_6",
                "parent_id": "PARENT_GRANULE_ID_6",
                "region_id": "55DCF",
                "processing_dt": BT - td(hours=26),
                "center_dt": BT - td(hours=32),
            }
        ),
        Actual(
            **{
                "dataset_id": "GRANULE_ID_7",
                "parent_id": "PARENT_GRANULE_ID_7",
                "region_id": "55DCF",
                "processing_dt": BT - td(hours=50),
                "center_dt": BT - td(hours=53),
            }
        ),
        Actual(
            **{
                "dataset_id": "GRANULE_ID_8",
                "parent_id": "PARENT_GRANULE_ID_8",
                "region_id": "XX000",
                "processing_dt": BT - td(hours=22),
                "center_dt": BT - td(hours=27),
            }
        ),  # product not in AOI
    ]
    ACTUAL_PRODUCTS2 = [  # Don't match with anything in expected
        Actual(
            **{
                "dataset_id": "GRANULE_ID_11",
                "parent_id": "PARENT_GRANULE_ID_11",
                "region_id": "54DFT",
                "processing_dt": BT,
                "center_dt": BT - td(hours=6),
            }
        ),
        Actual(
            **{
                "dataset_id": "GRANULE_ID_12",
                "parent_id": "PARENT_GRANULE_ID_12",
                "region_id": "54DFT",
                "processing_dt": BT - td(hours=24),
                "center_dt": BT - td(hours=28),
            }
        ),
        Actual(
            **{
                "dataset_id": "GRANULE_ID_15",
                "parent_id": "PARENT_GRANULE_ID_15",
                "region_id": "54DFT",
                "processing_dt": BT + td(hours=48),
                "center_dt": BT + td(hours=43),
            }
        ),  # tile in region, but not in expected (date error)
        Actual(
            **{
                "dataset_id": "GRANULE_ID_16",
                "parent_id": "PARENT_GRANULE_ID_16",
                "region_id": "55DCF",
                "processing_dt": BT - td(hours=26),
                "center_dt": BT - td(hours=32),
            }
        ),
        Actual(
            **{
                "dataset_id": "GRANULE_ID_17",
                "parent_id": "PARENT_GRANULE_ID_17",
                "region_id": "55DCF",
                "processing_dt": BT - td(hours=50),
                "center_dt": BT - td(hours=53),
            }
        ),
        Actual(
            **{
                "dataset_id": "GRANULE_ID_18",
                "parent_id": "PARENT_GRANULE_ID_18",
                "region_id": "XX000",
                "processing_dt": BT - td(hours=22),
                "center_dt": BT - td(hours=27),
            }
        ),  # product not in AOI
    ]
    EXPECTED_PRODUCTS = [
        Expected(**{"dataset_id": "PARENT_GRANULE_ID_1", "region_id": "54DFT"}),
        Expected(**{"dataset_id": "PARENT_GRANULE_ID_2", "region_id": "54DFT"}),
        Expected(**{"dataset_id": "PARENT_GRANULE_ID_3", "region_id": "54DFT"}),
        Expected(**{"dataset_id": "PARENT_GRANULE_ID_4", "region_id": "54DFT"}),
        Expected(**{"dataset_id": "PARENT_GRANULE_ID_6", "region_id": "55DCF"}),
        Expected(**{"dataset_id": "PARENT_GRANULE_ID_7", "region_id": "55DCF"}),
        Expected(
            **{"dataset_id": "PARENT_GRANULE_ID_8", "region_id": "00XXX"}
        ),  # product not in AOI
    ]

    def test_filter_datasets_to_region_returns_filtered_list_of_odc_products(self):
        filtered_list = filter_datasets_to_region(self.ACTUAL_PRODUCTS, "54DFT")
        self.assertEqual(len(filtered_list), 3)
        self.assertEqual(filtered_list[0].region_id, "54DFT")
        self.assertEqual(filtered_list[-1].region_id, "54DFT")

        filtered_list = filter_datasets_to_region(self.ACTUAL_PRODUCTS, "55DCF")
        self.assertEqual(filtered_list[0].region_id, "55DCF")
        self.assertEqual(filtered_list[-1].region_id, "55DCF")

        filtered_list = filter_datasets_to_region(self.ACTUAL_PRODUCTS, "55KHG")
        self.assertEqual(len(filtered_list), 0)

    def test_filter_datasets_to_region_returns_filtered_list_of_s2_products(self):
        filtered_list = filter_datasets_to_region(self.EXPECTED_PRODUCTS, "54DFT")
        self.assertEqual(len(filtered_list), 4)
        self.assertEqual(filtered_list[0].region_id, "54DFT")
        self.assertEqual(filtered_list[-1].region_id, "54DFT")

        filtered_list = filter_datasets_to_region(self.EXPECTED_PRODUCTS, "55DCF")
        self.assertEqual(filtered_list[0].region_id, "55DCF")
        self.assertEqual(filtered_list[-1].region_id, "55DCF")

        filtered_list = filter_datasets_to_region(self.EXPECTED_PRODUCTS, "55KHG")
        self.assertEqual(len(filtered_list), 0)

    def test_get_expected_ids_missing_in_actual(self):
        r_expected_products = filter_datasets_to_region(self.EXPECTED_PRODUCTS, "54DFT")
        r_actual_products = filter_datasets_to_region(self.ACTUAL_PRODUCTS, "54DFT")
        result = get_expected_ids_missing_in_actual(
            r_expected_products, r_actual_products
        )
        self.assertTrue("PARENT_GRANULE_ID_3" in result)
        self.assertTrue("PARENT_GRANULE_ID_4" in result)

        r_expected_products = filter_datasets_to_region(self.EXPECTED_PRODUCTS, "55DCF")
        r_actual_products = filter_datasets_to_region(self.ACTUAL_PRODUCTS, "55DCF")
        result = get_expected_ids_missing_in_actual(
            r_expected_products, r_actual_products
        )
        self.assertEqual(len(result), 0)

    def test_get_products_in_expected_and_actual(self):
        r_expected_products = filter_datasets_to_region(self.EXPECTED_PRODUCTS, "54DFT")
        r_actual_products = filter_datasets_to_region(self.ACTUAL_PRODUCTS, "54DFT")
        result = get_datasets_in_expected_and_actual(
            r_expected_products, r_actual_products
        )
        self.assertTrue("GRANULE_ID_1" in [x.dataset_id for x in result])
        self.assertTrue("GRANULE_ID_2" in [x.dataset_id for x in result])
        self.assertTrue("GRANULE_ID_5" not in [x.dataset_id for x in result])

    def test_calculate_metric_for_region(self):
        # Case1 54DFT
        r_expected_products = filter_datasets_to_region(self.EXPECTED_PRODUCTS, "54DFT")
        r_actual_products = filter_datasets_to_region(self.ACTUAL_PRODUCTS, "54DFT")
        result = calculate_metric_for_region(r_expected_products, r_actual_products)
        self.assertEqual(result["completeness"], 50.0)
        self.assertEqual(result["expected"], 4)
        self.assertEqual(result["missing"], 2)
        self.assertEqual(result["actual"], 2)
        self.assertEqual(len(result["missing_ids"]), 2)
        self.assertTrue("PARENT_GRANULE_ID_3" in result["missing_ids"])
        self.assertTrue("PARENT_GRANULE_ID_4" in result["missing_ids"])
        self.assertEqual(result["latest_sat_acq_ts"], self.BT - td(hours=6))
        self.assertEqual(result["latest_processing_ts"], self.BT)

        # Case2 55DCF (100% completeness)
        r_expected_products = filter_datasets_to_region(self.EXPECTED_PRODUCTS, "55DCF")
        r_actual_products = filter_datasets_to_region(self.ACTUAL_PRODUCTS, "55DCF")
        result = calculate_metric_for_region(r_expected_products, r_actual_products)
        self.assertEqual(result["completeness"], 100.0)
        self.assertEqual(result["expected"], 2)
        self.assertEqual(result["missing"], 0)
        self.assertEqual(result["actual"], 2)
        self.assertEqual(len(result["missing_ids"]), 0)
        self.assertEqual(result["latest_sat_acq_ts"], self.BT - td(hours=32))
        self.assertEqual(result["latest_processing_ts"], self.BT - td(hours=26))

        # Case3 55KHG (Edge case, after filtering, no expected, no actuals)
        r_expected_products = filter_datasets_to_region(self.EXPECTED_PRODUCTS, "55KHG")
        r_actual_products = filter_datasets_to_region(self.ACTUAL_PRODUCTS, "55KHG")
        result = calculate_metric_for_region(r_expected_products, r_actual_products)
        self.assertEqual(result["completeness"], None)
        self.assertEqual(result["expected"], 0)
        self.assertEqual(result["missing"], 0)
        self.assertEqual(result["actual"], 0)
        self.assertEqual(len(result["missing_ids"]), 0)
        self.assertEqual(result["latest_sat_acq_ts"], None)
        self.assertEqual(result["latest_processing_ts"], None)

    def test_calculate_metrics_for_all_regions(self):
        result = calculate_metrics_for_all_regions(
            self.EXPECTED_PRODUCTS, self.ACTUAL_PRODUCTS, self.AOI_LIST
        )
        self.assertEqual(len(result), 3)
        self.assertTrue("54DFT" in [x["region_id"] for x in result])
        self.assertTrue("55DCF" in [x["region_id"] for x in result])
        self.assertTrue("55KHG" in [x["region_id"] for x in result])

    def test_calculate_summary_stats(self):
        output = calculate_metrics_for_all_regions(
            "s2a", self.AOI_LIST, self.EXPECTED_PRODUCTS, self.ACTUAL_PRODUCTS
        )
        result = calculate_summary_stats(output)
        self.assertEqual(result["expected"], 6)
        self.assertEqual(result["missing"], 2)
        self.assertEqual(result["actual"], 4)
        self.assertAlmostEqual(result["completeness"], 66.66666666)
        self.assertEqual(result["latest_sat_acq_ts"], self.BT - td(hours=6))
        self.assertEqual(result["latest_processing_ts"], self.BT)

    def test_calculate_summary_stats(self):
        """This is an edge case where no actual products match expected"""
        output = calculate_metrics_for_all_regions(
            self.EXPECTED_PRODUCTS, self.ACTUAL_PRODUCTS2, self.AOI_LIST
        )
        result = calculate_summary_stats(output)
        self.assertEqual(result["expected"], 6)
        self.assertEqual(result["missing"], 6)
        self.assertEqual(result["actual"], 0)
        self.assertAlmostEqual(result["completeness"], 0)
        self.assertEqual(result["latest_sat_acq_ts"], None)
        self.assertEqual(result["latest_processing_ts"], None)


if __name__ == "__main__":
    unittest.main(verbosity=1)
