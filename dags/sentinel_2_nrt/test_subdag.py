from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from textwrap import dedent


def subdag_test(parent_dag_name, child_dag_name, args, xcom_task_id):

    dag_subdag = DAG(
        dag_id="%s.%s" % (parent_dag_name, child_dag_name),
        default_args=args,
        catchup=False,
    )

    bash_cmd = [
        "bash",
        "-c",
        dedent(
            """
            for product in %s; do
                echo $product;
            done;
        """
        )
        % ("{{ task_instance.xcom_pull(dag_id='utility_explorer-refresh-stats', task_ids='parse_dagrun_conf') }}"),
    ]

    # BashOperator(task_id='t2', bash_command="echo product is set to: %s" %(refresh_products), dag=dag_subdag)
    BashOperator(task_id='t3', bash_command=bash_cmd, dag=dag_subdag)
    return dag_subdag