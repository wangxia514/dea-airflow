import unittest
from dags.utility.utility_ows_update_extent import dag


class testClass(unittest.TestCase):
    def assertDagDictEqual(self, source, dag):
        assert dag.task_dict.keys() == source.keys()
        for task_id, downstream_list in source.items():
            assert dag.has_task(task_id)
            task = dag.get_task(task_id)
            assert task.downstream_task_ids == set(downstream_list)

    def test_dag(self):
        self.assertDagDictEqual(
            {
                "DummyInstruction_0": ["DummyInstruction_1"],
                "DummyInstruction_1": ["DummyInstruction_2"],
                "DummyInstruction_2": ["DummyInstruction_3"],
                "DummyInstruction_3": [],
            },
            dag,
        )
