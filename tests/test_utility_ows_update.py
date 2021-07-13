from datetime import datetime

from airflow import DAG
from airflow.models import TaskInstance, DagRun

from dea_utils.update_explorer_summaries import explorer_refresh_operator
from dea_utils.update_ows_products import ows_update_operator


def test_utility_ows_update():
    with DAG(dag_id="ows_update_test", start_date=datetime(2021, 1, 1)) as dag:
        task1 = ows_update_operator(dag=dag)
        task2 = ows_update_operator(dag=dag)
    ti = TaskInstance(task=task1, execution_date=datetime.now())

    # Test using the default set of OWS products
    template_context = ti.get_template_context()
    template_context["dag_run"] = DagRun()
    assert template_context

    task1.render_template_fields(template_context)
    assert "for product in s2_nrt_granule_nbar_t wofs_albers" in task1.arguments[2]

    # Test overriding the products using dag_run.conf
    dag_run = DagRun()
    dag_run.conf = {"products": "hello world"}
    template_context["dag_run"] = dag_run

    task2.render_template_fields(template_context)
    assert task2.arguments
    assert "for product in hello world" in task2.arguments[2]


def test_explorer_update():
    with DAG(dag_id="ows_update_test", start_date=datetime(2021, 1, 1)) as dag:
        task1 = explorer_refresh_operator()
        task2 = explorer_refresh_operator()
    ti = TaskInstance(task=task1, execution_date=datetime.now())
