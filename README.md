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
Docker Compose. Full instruction is available from here: https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html

First, initialise some environment variables:

``` bash
mkdir ./dags ./logs ./plugins # you will notice plugins and dags folder already exist
echo -e "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" >> .env
```

Then start up `docker-compose`:

``` bash
docker-compose up airflow-init
docker-compose up
```
Connect to the [Local Airflow Webserver](http://localhost:8080/) in your browser, and login with Username: `airflow`,
Password: `airflow`.

#### Troubleshooting
if you are experiencing issues with the docker-compose file, please ensure to check your docker-compose version, it is confirmed to work
with version `1.29.2`

``` bash
ubuntu@:~/dea-airflow$ docker-compose version
docker-compose version 1.29.2, build 5becea4c
docker-py version: 5.0.0
CPython version: 3.7.10
OpenSSL version: OpenSSL 1.1.0l  10 Sep 2019
```

## Local Editing of DAG's

DAGs can be locally edited and validated. Development can be done in `conda` or `venv` according to developer preference. Grab everything airflow and write DAGs. Use `autopep8` and `pylint` to achieve import validation and consistent formatting as the CI pipeline for this repository matures.

```bash
pip install apache-airflow[aws,kubernetes,postgres,redis,ssh,celery] -c constraints.txt
pip install pylint pylint-airflow

pylint dags plugins
```

## Pre-commit setup

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