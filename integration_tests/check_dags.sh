#!/usr/bin/env bash
# Convenience script for running Travis-like checks.
set -ex

airflow dags list-runs -d deletion_utility_select_dataset_in_years -v > run_result.txt

if grep -rniw './run_result.txt' -e 'Failed'; then
   echo "Tests failed"
   exit 1
fi
