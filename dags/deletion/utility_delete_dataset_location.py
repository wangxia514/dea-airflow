"""
## Utility Tool (Self Serve)
For updating datasets location when dataset location have been changed, examples cases:

- dev s3 files promoted to production s3 buckets
- file path and subpath changed
- general file restructuring

### ODC DB dataset_location table structure

```
odc=> select * from agdc.dataset_location limit 5;
 id |             dataset_ref              | uri_scheme |                                                uri_body                                                 |             added             | added_by | archived
----+--------------------------------------+------------+---------------------------------------------------------------------------------------------------------+-------------------------------+----------+----------
  1 | 1e5b4bfa-50f0-4894-a1fb-745935effe82 | s3         | //dea-public-data/geomedian-australia/v2.1.0/L8/x_-1/y_-10/2014/01/01/ls8_gm_nbart_-1_-10_20140101.yaml | 2019-06-05 03:06:12.900472+00 | ows      |
  2 | f875b55e-b8df-4c0f-8016-716af601603b | s3         | //dea-public-data/geomedian-australia/v2.1.0/L8/x_-1/y_-12/2014/01/01/ls8_gm_nbart_-1_-12_20140101.yaml | 2019-06-05 03:06:13.030919+00 | ows      |
  3 | 8e080699-7869-4a12-9c7a-cbe264857f96 | s3         | //dea-public-data/geomedian-australia/v2.1.0/L8/x_-1/y_-12/2017/01/01/ls8_gm_nbart_-1_-12_20170101.yaml | 2019-06-05 03:06:13.192114+00 | ows      |
  4 | 00f5dc60-47d0-4ed2-8ea3-fdb5674de28c | s3         | //dea-public-data/geomedian-australia/v2.1.0/L8/x_-1/y_-13/2015/01/01/ls8_gm_nbart_-1_-13_20150101.yaml | 2019-06-05 03:06:13.378298+00 | ows      |
  5 | 507d7581-2b53-45a5-84b1-b1413f4a459e | s3         | //dea-public-data/geomedian-australia/v2.1.0/L8/x_-1/y_-11/2013/01/01/ls8_gm_nbart_-1_-11_20130101.yaml | 2019-06-05 03:06:13.406177+00 | ows      |
```

## Prevention Mechanisms
Before the deletion query is executed, the dag checks the following two conditions:

- do all the datasets for the product has more than 1 location
- is the `uri_pattern` returning more than 1 matching product

if any of the above condition is not met, the dag will exit.

`uri_pattern` can be grabed from explorer `https://explorer.dev.dea.ga.gov.au/products/<product_name>/datasets` select a dataset and under `Locations` section

## Note
All list of utility dags here: https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/utility, see Readme

#### Utility customisation

#### example conf in json format

    {
        "uri_pattern": "dea-public-data-dev/s2be/",
        "product_name": "s2_barest_earth"
    }

"""
from datetime import datetime, timedelta

from airflow import DAG

from airflow.kubernetes.secret import Secret
from airflow.hooks.postgres_hook import PostgresHook
from deletion.deletion_sql_queries import (
    CONFIRM_DATASET_HAS_MORE_THAN_ONE_LOCATION,
    SELECT_ALL_PRODUCTS_MATCHING_URI_PATTERNS,
)

from airflow.providers.postgres.operators.postgres import PostgresOperator
from infra.connections import DB_ODC_READER_CONN

from airflow.operators.python_operator import PythonOperator
from infra.variables import (
    AWS_DEFAULT_REGION,
)
from airflow.exceptions import AirflowException

DAG_NAME = "deletion_utility_datacube_dataset_location"

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
}


def check_dataset_location(product_name="", uri_pattern="", **kwargs):
    """
    return sql query result
    """
    # setup connections
    pg_hook = PostgresHook(postgres_conn_id=DB_ODC_READER_CONN)
    connection = pg_hook.get_conn()
    cursor = connection.cursor()

    # SQL
    check_if_only_one_location = CONFIRM_DATASET_HAS_MORE_THAN_ONE_LOCATION.format(
        product_name=product_name
    )

    cursor.execute(check_if_only_one_location)
    count_dataset_location_more_than_one = cursor.fetchone()
    print("check the datasets for the product all contain more than 1 location")
    print(count_dataset_location_more_than_one)
    if (
        not count_dataset_location_more_than_one
        or count_dataset_location_more_than_one[0] == 0
    ):
        raise AirflowException(
            "The datasets for the product only has one location, exiting"
        )  # mark it failed

    # check URI match and product matches
    # SQL
    check_uri_pattern = SELECT_ALL_PRODUCTS_MATCHING_URI_PATTERNS.format(
        uri_pattern=uri_pattern
    )

    cursor.execute(check_uri_pattern)
    count_product_match_uri_pattern = cursor.fetchone()
    print("check uri pattern matches for only one product")
    print(count_product_match_uri_pattern)
    if not count_product_match_uri_pattern or count_product_match_uri_pattern[0] > 1:
        raise AirflowException(
            "There are more than one product match the uri pattern, the uri pattern can be better refined, exiting"
        )  # mark it failed


# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "datacube-dataset-location-deletion", "self-service"],
)


with dag:

    check_dataset_location = PythonOperator(
        task_id="check_dataset_location",
        python_callable=check_dataset_location,
        op_kwargs={
            "uri_pattern": "{{ dag_run.conf.uri_patern }}",
            "product_name": "{{ dag_run.conf.product_name }}",
        },
    )

    delete_location = PostgresOperator(
        task_id="delete_location",
        sql="""
            DELETE
            FROM
                agdc.dataset_location dl
            WHERE
                dl.uri_body LIKE '%{{ params.uri_pattern }}%'
                AND
                    dl.dataset_ref
                    IN (
                        SELECT id from agdc.dataset where dataset_type_ref = (
                            select id from agdc.dataset_type where name = '{{ params.product_name }}'
                        )
                    );
        """,
        postgres_conn_id=DB_ODC_READER_CONN,
        params={
            "uri_pattern": "{{ dag_run.conf.uri_patern }}",
            "product_name": "{{ dag_run.conf.product_name }}",
        },
    )
