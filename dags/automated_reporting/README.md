# Automated Reporting Dags

Automated ETLs are run from dags in this folder. All reporting dags are prefixed with `rep` and have a tag `reporting`. Production dags are suffixed with `_prod`.

These dags are used purely as schedulers for running and reporting on Python ETLs located in the `https://bitbucket.org/geoscienceaustralia/automated-reporting-etl/` repo. They contain minimal ETL code.

All dags use the KubernetesPodOperator to provide standard Python environment, and install the reporting-etl python package, run task. e.g.
```
echo DEA ODC Currency job started: $(date)
pip install ga-reporting-etls==2.2.2
odc-currency
```

The exception to this are some dags that backup and restore the reporting database, which purely run bash commands and have no code in the reporting ETL repo.

## Secrets

Talk to Ram or Tom about how to expose secrets to the Kuberenetes jobs.


## Development Dags

These are used for testing. They are run in the sandbox, rather than dev Airflow environment as the dev Airflow environment has no reporting database issue. The have a tag `reporting-dev` and names are suffixed with `_dev`.


## ToDo
  - Use an image with the reporting etls Python package installed, rather than PyPi hosted Python Package.
  - Change all dags to use SSM Parameters/Kubernetes secrets
