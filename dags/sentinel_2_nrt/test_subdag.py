from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator

from textwrap import dedent


def subdag_test(parent_dag_name, child_dag_name, args, xcom_task_id=None):

    dag_subdag = DAG(
        dag_id="%s.%s" % (parent_dag_name, child_dag_name),
        default_args=args,
        catchup=False,
    )
    if xcom_task_id:
        products = (
            "{{{{ task_instance.xcom_pull(dag_id='{}', task_ids='{}') }}}}".format(
                parent_dag_name, xcom_task_id
            )
        )
    else:
        products = "A B"

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
        % (products),
    ]



    # BashOperator(task_id='t2', bash_command="echo product is set to: %s" %(refresh_products), dag=dag_subdag)
    KubernetesPodOperator(
        namespace="processing",
        image="ubuntu:latest",
        cmds=["bash", "-c"],
        arguments=["echo", "dbname:", "$DB_HOSTNAME"],
        # arguments=bash_cmd,
        labels={"foo": "bar"},
        name="test-cmd",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="task-two",
        get_logs=True,
        dag=dag_subdag,
    )
    return dag_subdag
