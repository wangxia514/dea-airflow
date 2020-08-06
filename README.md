# Geoscience Australia DEA Airflow DAGs repository

## Development

### Local Editing of DAGs

DAG's can be locally edited and validated. Development can be done in `conda` or `venv` according to developer preference. Grab everything airflow and write DAGs. Use `autopep8` and `pylint` to achieve import validation and consistent formatting as the CI pipeline for this repository matures.

```bash
pip install apache-airflow[aws,kubernetes,postgres,redis,ssh,celery]
pip install pylint pylint-airflow

pylint dags plugins
```
