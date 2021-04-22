from pathlib import Path
import pytest
from airflow import models as airflow_models

DAG_PATHS = (Path(__file__).parent.parent / "dags").rglob("*.py")

@pytest.mark.parametrize("dag_path", DAG_PATHS)
def test_dag_integrity(dag_path: Path):
    """Import DAG files and check for a valid DAG instance."""
    dag_name = dag_path.stem
    module = _import_file(dag_name, dag_path)

    # Validate if there is at least 1 DAG object in the file
    dag_objects = [
        var
        for var in vars(module).values()
        if isinstance(var, airflow_models.DAG)
    ]

    # For every DAG object, test for cycles
    for dag in dag_objects:
        dag.test_cycle()  # Test for cycles

def _import_file(module_name, module_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
