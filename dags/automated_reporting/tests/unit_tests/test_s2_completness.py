# pylint: skip-file
import unittest

from automated_reporting.tasks.s2_completeness import filter_expected_to_sensor


# Unit Tests
class TestS2CompletenessUnit(unittest.TestCase):

    EXPECTED_PRODUCTS = [
        {"dataset_id": "PARENT_GRANULE_ID_1", "region_id": "54DFT", "sensor": "s2a"},
        {"dataset_id": "PARENT_GRANULE_ID_2", "region_id": "54DFT", "sensor": "s2a"},
        {"dataset_id": "PARENT_GRANULE_ID_3", "region_id": "54DFT", "sensor": "s2a"},
        {"dataset_id": "PARENT_GRANULE_ID_4", "region_id": "54DFT", "sensor": "s2b"},
        {"dataset_id": "PARENT_GRANULE_ID_5", "region_id": "55DCF", "sensor": "s2b"},
    ]

    def test_filter_exptected_to_sensor(self):
        result = filter_expected_to_sensor(self.EXPECTED_PRODUCTS, "s2a")
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["sensor"], "s2a")

        result = filter_expected_to_sensor(self.EXPECTED_PRODUCTS, "s2b")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["sensor"], "s2b")


if __name__ == "__main__":
    unittest.main(verbosity=1)
