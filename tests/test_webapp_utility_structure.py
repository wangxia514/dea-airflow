import unittest
from utility.utility_ows_update_extent import dag


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

    def test_dag(self):
        self.assertDagDictEqual(
            {
                "parse_dagrun_conf": ["run-ows-update-ranges"],
                "run-ows-update-ranges": [],
            },
            dag,
        )
