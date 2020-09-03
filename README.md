# Geoscience Australia DEA Airflow DAGs repository

## Deployment Workflow

This repository contains two branches, `master` and `develop`.

The `master` branch requires Pull Requests and code reviews to merge code into
it. It deploys automatically to the [Production (Sandbox) Airflow deployment](https://airflow.sandbox.dea.ga.gov.au/home).

The `develop` branch accepts pushes directly, or via Pull Request, and deploys
automatically to the [Development Airflow](https://airflow.dev.dea.ga.gov.au/home).

We're not happy with this strategy, and are looking for an alternative that
doesn't have us deploying and inadvertently running code in multiple places by
accident, but haven't come up with anything yet.

## Development Using Docker

If you have Docker available, by far the easiest development setup is to use
Docker Compose.

``` bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' 
docker-compose up

docker-compose exec webserver /bin/bash
. /entrypoint.sh
airflow connections --add --conn_id lpgs_gadi --conn_uri 'ssh://dra547@gadi.nci.org.au'

```

``` bash
docker-compose up
docker-compose exec 
docker-compose run --rm webserver airflow upgradedb
docker-compose run --rm webserver airflow connections --add --conn_id lpgs_gadi --conn_uri ssh://dra547@gadi.nci.org.au/
docker-compose exec webserver /entrypoint.sh airflow connections --add --conn_id dea_public_data_upload --conn_uri s3://foo:bar@dea-public-data-dev/
```

## Local Editing of DAG's

DAGs can be locally edited and validated. Development can be done in `conda` or `venv` according to developer preference. Grab everything airflow and write DAGs. Use `autopep8` and `pylint` to achieve import validation and consistent formatting as the CI pipeline for this repository matures.

```bash
pip install apache-airflow[aws,kubernetes,postgres,redis,ssh,celery]
pip install pylint pylint-airflow

pylint dags plugins
```

### Pre-commit setup

A [pre-commit](https://pre-commit.com/) config is provided to automatically format
and check your code changes. This allows you to immediately catch and fix
issues before you raise a failing pull request (which run the same checks under
Travis).

If you don't use Conda, install pre-commit from pip:

    pip install pre-commit

If you do use Conda, install from conda-forge (*required* because the pip
version uses virtualenvs which are incompatible with Conda's environments)

    conda install pre_commit

Now install the pre-commit hook to the current repository:

    pre-commit install

Your code will now be formatted and validated before each commit. You can also
invoke it manually by running `pre-commit run --all-files`
