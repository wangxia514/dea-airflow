"""
# Build new `dea` module on the NCI

"""
from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from datetime import datetime, timedelta
import pytz

default_args = {
    'owner': 'Damien Ayers',
    'start_date': datetime(2020, 3, 12),
    'retries': 0,
    'timeout': 1200,  # For running SSH Commands
    'email_on_failure': True,
    'email': 'damien.ayers@ga.gov.au',
}

dag = DAG(
    'nci_build_dea_module',
    default_args=default_args,
    schedule_interval=None,
    tags=['nci'],
)

timezone = pytz.timezone("Australia/Canberra")

with dag:
    build_env_task = SSHOperator(
        task_id=f'build_dea_module',
        ssh_conn_id='lpgs_gadi',
        command=f"""
        rm -r /g/data/v10/public/modules/dea/{datetime.datetime.now(datetime.datetime.now(timezone)).strftime("%Y%m%d")}
        set -eux
        cd ~/dea-orchestration/
        git reset --hard
        git pull
        cd ~/dea-orchestration/nci_environment
        git status
        module load python3/3.7.4
        pip3 install --user pyyaml jinja2
        
        ./build_environment_module.py dea/modulespec.yaml
        """,
    )

    test_env_task = SSHOperator(
        task_id='test_dea_module',
        ssh_conn_id='lpgs_gadi',
        command="""
        set -eux
        cd $TMPDIR
        rm -rf dea-notebooks
        git clone --depth 1 https://github.com/GeoscienceAustralia/dea-notebooks
        cd dea-notebooks/Frequently_used_code/
        module load dea/$(date +%Y%m%d)  # TODO, this will fail if run over midnight...

        python -m pytest --nbval-lax Applying_WOfS_bitmasking.ipynb Calculating_band_indices.ipynb \
        Contour_extraction.ipynb Exporting_GeoTIFFs.ipynb Exporting_NetCDFs.ipynb \
        Imagery_on_web_map.ipynb Integrating_external_data.ipynb Machine_learning_with_ODC.ipynb \
        Masking_data.ipynb Opening_GeoTIFFs_NetCDFs.ipynb Pan_sharpening_Brovey.ipynb \
        Rasterize_vectorize.ipynb Using_load_ard.ipynb Virtual_products.ipynb Working_with_time.ipynb

        """
    )

    build_env_task >> test_env_task
