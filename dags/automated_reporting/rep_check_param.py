# You can pass `params` dict to DAG object
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': airflow.utils.dates.days_ago(2),
}

dag = DAG(
    dag_id='airflow_tutorial_2',
    default_args=default_args,
    schedule_interval=None,
    params={
        "param1": "value1",
        "param2": "value2"
    }
)

bash = BashOperator(
    task_id='bash',
    bash_command='echo {{ params.param1 }}', # Output: value1
    dag=dag
)
