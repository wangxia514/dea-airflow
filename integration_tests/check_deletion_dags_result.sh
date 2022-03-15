#!/usr/bin/env bash
set -ex

# test delete datasets by years
test_dag=deletion_utility_select_dataset_in_years

if airflow dags list-runs -d $test_dag -v  2>&1 | grep $test_dag | grep -i 'failed'; then
   echo "Tests failed, both dag run for $test_dag"
   exit 1
fi

# test delete datasets by uri pattern

test_dag=deletion_utility_datacube_dataset_location

if [ $(airflow dags list-runs -d $test_dag -v  2>&1 | grep $test_dag | grep -i 'failed' | wc -l) != 2 ]; then
   echo "Tests failed, there should be 2 failed dag runs for $test_dag"
   exit 1
fi

if [ $(airflow dags list-runs -d $test_dag -v  2>&1 | grep $test_dag | grep -i 'success' | wc -l) != 1 ]; then
   echo "Tests failed, there should be 1 success dag run for $test_dag"
   exit 1
fi

test_dag=deletion_utility_datasets_version_sensor

if [ $(airflow dags list-runs -d $test_dag -v  2>&1 | grep $test_dag | grep -i 'success' | wc -l) != 1 ]; then
   echo "Tests failed, there should be 1 success dag run for $test_dag"
   exit 1
fi

if [ $(airflow dags list-runs -d $test_dag -v  2>&1 | grep $test_dag | grep -i 'failed' | wc -l) != 1 ]; then
   echo "Tests failed, there should be 1 success dag run for $test_dag"
   exit 1
fi
