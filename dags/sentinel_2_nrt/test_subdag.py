from airflow import DAG
from airflow.operators.bash_operator import BashOperator


def subdag_test(parent_dag_name, child_dag_name, args, refresh_products):

    dag_subdag = DAG(
        dag_id="%s.%s" % (parent_dag_name, child_dag_name),
        default_args=args,
        catchup=False,
    )

    BashOperator(task_id='t2', bash_command="echo product is set to: %s" %(refresh_products), dag=dag_subdag)

    return dag_subdag