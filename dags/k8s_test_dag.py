from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator


default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 11),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

pipeline = DAG(
    "k8s_test_dag",
    doc_md=__doc__,
    default_args=default_args,
    description="test dag please ignore",
    catchup=False,
    params={},
    schedule_interval=None,  # timedelta(minutes=30),
    tags=["k8s", "dea", "psc", "wagl", "nrt"],
)


def send(**context):
    return {"dataset": "dataset-to-index"}


def receive(**context):
    task_instance = context["task_instance"]
    msg = task_instance.xcom_pull(task_ids="send", key="return_value")

    print(msg)


with pipeline:
    SEND = PythonOperator(
        task_id="send",
        python_callable=send,
        provide_context=True,
    )

    RECEIVE = PythonOperator(
        task_id="receive",
        python_callable=receive,
        provide_context=True,
    )

    SEND >> RECEIVE
