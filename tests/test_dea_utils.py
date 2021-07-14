from datetime import datetime

from airflow import DAG
from airflow.models import TaskInstance, DagRun

from dea_utils.update_explorer_summaries import explorer_refresh_operator
from dea_utils.update_ows_products import ows_update_operator


def test_utility_ows_update():
    with DAG(dag_id="ows_update_test", start_date=datetime(2021, 1, 1)) as dag:
        task1 = ows_update_operator("space separated list", dag=dag)
        task2 = ows_update_operator("{{ dag_run.conf.products }}", dag=dag)
        task3 = ows_update_operator(["list", "of", "products"], dag=dag)
    ti = TaskInstance(task=task1, execution_date=datetime.now())

    # Test using the default set of OWS products
    template_context = ti.get_template_context()
    template_context["dag_run"] = DagRun()
    assert template_context

    task1.render_template_fields(template_context)
    assert "for product in space separated list" in task1.arguments[2]

    # Test overriding the products using dag_run.conf
    dag_run = DagRun()
    dag_run.conf = {"products": "hello world"}
    template_context["dag_run"] = dag_run

    task2.render_template_fields(template_context)
    assert task2.arguments
    assert "for product in hello world" in task2.arguments[2]

    # Test 3: supplying a list of products when creating the task
    assert "for product in list of products" in task3.arguments[2]


def test_explorer_update():
    with DAG(dag_id="ows_update_test", start_date=datetime(2021, 1, 1)) as dag:
        task1 = explorer_refresh_operator("space separated list")
        task2 = explorer_refresh_operator("{{ dag_run.conf.products }}")
        task3 = explorer_refresh_operator(["list", "of", "products"])
    ti = TaskInstance(task=task1, execution_date=datetime.now())
    template_context = ti.get_template_context()

    # Test task1 arguments is populated using the supplied string
    assert (
        "cubedash-gen -v --no-init-database --refresh-stats space separated list"
        in task1.arguments[2]
    )

    # Test task2 after templating is populated with a user DagRun supplied set of products
    dag_run = DagRun()
    dag_run.conf = {"products": "hello world"}
    template_context["dag_run"] = dag_run

    task2.render_template_fields(template_context)
    assert (
        "cubedash-gen -v --no-init-database --refresh-stats hello world"
        in task2.arguments[2]
    )

    # Test task3 uses a correctly expanded list of products
    assert (
        "cubedash-gen -v --no-init-database --refresh-stats list of products"
        in task3.arguments[2]
    )
