"""
# Update NCI Explorer Database

Visit [NCI Explorer](https://explorer.nci.dea.ga.gov.au/).

<details>
    <summary><b>Instructions for creating the Datacube Explorer code/environment on NCI (click)</b></summary>

<ol>
    <li><a href="https://docs.conda.io/en/latest/miniconda.html">Install miniconda</a> </li>
    <li>Install <code>mamba</code> by running <code>conda install mamba</code>.</li>
    <li>Create an environment template with the follow contents:

<pre>
# Execute with:
#
#   mamba env create -p /g/data/v10/private/cubedash_env/ --file cubdashenv.yml
#
name: cubedash_env
channels:
  - conda-forge
dependencies:
  - python=3.9
  - datacube
  - pip
  - pip:
    - datacube-explorer
</pre>
</li>
    <li>Create the new environment by running:
    <pre>mamba env create -p /g/data/v10/private/cubedash_env/ --file
    cubdashenv.yml</pre></li>
</ol>


</details>

"""
from datetime import datetime
from textwrap import dedent

import pendulum
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator

local_tz = pendulum.timezone("Australia/Canberra")

dag = DAG(
    "nci_update_explorer_tables",
    doc_md=__doc__,
    default_args={
        "owner": "Damien Ayers",
        "depends_on_past": False,
        "start_date": datetime(2022, 4, 12, tzinfo=local_tz),
        "email": [
            "damien.ayers@ga.gov.au",
            "david.gavin@ga.gov.au",
        ],
        "email_on_failure": True,
        "email_on_retry": False,
        "retries": 3,
        "retry_delay": 5 * 60,
        "ssh_conn_id": "lpgs_gadi",
    },
    catchup=False,
    schedule_interval="@daily",
    tags=["nci", "explorer"],
    default_view="tree",
)

with dag:
    update_explorer_tables = SSHOperator(
        command=dedent(
            """

            # export DATACUBE_CONFIG_PATH=/g/data/v10/public/modules/dea/20201217/datacube.conf
            export DB_DATABASE=datacube
            export DB_HOSTNAME=dea-db.nci.org.au
            # Bypass pgbouncer by connecting to 5432 to avoid timeouts
            export DB_PORT=5432

            source  /g/data/v10/private/miniconda3/etc/profile.d/conda.sh
            conda activate /g/data/v10/private/cubedash_env/

            cubedash-run --version

            cubedash-gen --all
        """
        ),
        task_id="update_nci_explorer_tables",
        timeout=2 * 60 * 60,
    )
