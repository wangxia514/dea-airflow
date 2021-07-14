import unittest
from utility.utility_ows_update_extent import dag as ows_utility_dag
from utility.utility_explorer_summary import dag as explorer_utility_dag
from utility.utility_annual_workflow import dag as annual_utility_dag
from utility.utility_odc_db_backup_to_s3 import dag as db_backup_utility_dag
from utility.utility_add_product import dag as add_product_index_utility_dag


class testClass(unittest.TestCase):
    def assertDagDictEqual(self, source, dag):
        self.assertEqual(dag.task_dict.keys(), source.keys())
        for task_id, downstream_list in source.items():
            self.assertTrue(
                dag.has_task(task_id), msg="Missing task_id: {} in dag".format(task_id)
            )
            task = dag.get_task(task_id)
            self.assertEqual(
                task.downstream_task_ids,
                set(downstream_list),
                msg="unexpected downstream link in {}".format(task_id),
            )

    def test_ows_utility_dag(self):
        self.assertDagDictEqual(
            {
                "ows-update-range": [],
            },
            ows_utility_dag,
        )

    def test_explorer_utility_dag(self):
        self.assertDagDictEqual(
            {
                "explorer-summary-task": [],
            },
            explorer_utility_dag,
        )

    def test_annual_utility_dag(self):
        self.assertDagDictEqual(
            {
                "batch-indexing-task": [
                    "explorer-summary-task",
                    "ows-update-range",
                ],
                "explorer-summary-task": [],
                "ows-update-range": [],
            },
            annual_utility_dag,
        )

    def test_db_backup_utility_dag(self):
        self.assertDagDictEqual(
            {
                "dump-odc-db": [],
            },
            db_backup_utility_dag,
        )

    def test_add_product_index_utility_dag(self):
        self.assertDagDictEqual(
            {
                "check_dagrun_config": ["add-product-task", "batch-indexing-task"],
                "add-product-task": ["batch-indexing-task"],
                "batch-indexing-task": ["explorer-summary-task"],
                "explorer-summary-task": [],
            },
            add_product_index_utility_dag,
        )