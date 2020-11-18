#!/usr/bin/env python3
"""
Script to sync Sentinel-2 data from NCI to AWS S3 bucket
"""

import logging
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import as_completed
from pathlib import Path

import click
import yaml
from odc.aws import s3_dump, s3_client
from odc.index import odc_uuid
from tqdm import tqdm

NCI_DIR = '/g/data/if87/datacube/002/S2_MSI_ARD/packaged'
S3_PATH = 'L2/sentinel-2-nbar/S2MSIARD_NBAR'
S3_BUCKET = 'dea-public-data'

S3 = None

_LOG = logging.getLogger()


def setup_logging():
    """Log to stdout (via TQDM if running interactively) as well as into a file."""
    _LOG.setLevel(logging.INFO)
    if sys.stdout.isatty():
        c_handler = TqdmLoggingHandler()
    else:
        c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler('s3_uploads.log')
    c_handler.setLevel(logging.INFO)
    f_handler.setLevel(logging.INFO)

    # Create formatters and add it to handlers
    # c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(formatter)
    f_handler.setFormatter(formatter)

    # Add handlers to the logger
    _LOG.addHandler(f_handler)
    _LOG.addHandler(c_handler)


@click.command()
@click.argument('s3_urls', type=click.File('r'))
@click.option('--workers', type=int, default=10)
def main(s3_urls, workers):
    """
    Script to sync Sentinel-2 data from NCI to AWS S3 bucket

    Pass in a file containing destination S3 urls that need to be uploaded.

    """
    setup_logging()

    global S3
    S3 = s3_client()
    urls_to_upload = [url.strip() for url in s3_urls.readlines()]

    _LOG.info(f"{len(urls_to_upload)} datasets to upload.")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(upload_dataset, s3_url) for s3_url in urls_to_upload]

        for future in tqdm(as_completed(futures), total=len(urls_to_upload), unit='datasets', disable=None):
            _LOG.info(f"Completed uploaded: {future.result()}")


def upload_dataset(s3_url):
    granule_id = s3_url_to_granule_id(s3_url)

    upload_dataset_without_yaml(granule_id, S3_BUCKET)

    local_path = Path(NCI_DIR) / granule_id
    upload_dataset_doc(local_path / 'ARD-METADATA.yaml', s3_url)
    return s3_url


def s3_url_to_granule_id(s3_url):
    match = re.search(r'/(\d\d\d\d-\d\d-\d\d/.*)/', s3_url)
    if match:
        return match.group(1)
    else:
        raise ValueError(f'Unable to extract granule id from {s3_url}')


def upload_dataset_without_yaml(granule_id, _s3_bucket):
    """
    Run AWS sync command to sync granules to S3 bucket
    :param granule_id: name of the granule
    :param _s3_bucket: name of the s3 bucket
    """
    local_path = Path(NCI_DIR) / granule_id
    s3_path = f"s3://{_s3_bucket}/{S3_PATH}/{granule_id}"

    # Remove any data that shouldn't be there and exclude the metadata and NBART
    command = f"aws s3 sync {local_path} {s3_path} " \
              "--only-show-errors " \
              "--delete " \
              "--exclude NBART/* " \
              "--exclude ARD-METADATA.yaml"

    try:
        subprocess.run(command, shell=True, check=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        _LOG.info(f"Upload failed, stdout: {e.stdout}, stderr: {e.stderr}")
        raise e


def upload_dataset_doc(src_yaml, s3_url):
    """
    Replace metadata with additional info
    :param src_yaml: metadata file in NCI
    :param s3_url: path to upload metadata to in s3
    """
    with open(src_yaml) as fin:
        nci_dataset = yaml.safe_load(fin)

    metadata_to_upload = munge_metadata(nci_dataset)

    s3_dump(yaml.safe_dump(metadata_to_upload, default_flow_style=False), s3_url, S3)


def munge_metadata(nci_dataset):
    del nci_dataset['image']['bands']['nbart_blue']
    del nci_dataset['image']['bands']['nbart_coastal_aerosol']
    del nci_dataset['image']['bands']['nbart_contiguity']
    del nci_dataset['image']['bands']['nbart_green']
    del nci_dataset['image']['bands']['nbart_nir_1']
    del nci_dataset['image']['bands']['nbart_nir_2']
    del nci_dataset['image']['bands']['nbart_red']
    del nci_dataset['image']['bands']['nbart_red_edge_1']
    del nci_dataset['image']['bands']['nbart_red_edge_2']
    del nci_dataset['image']['bands']['nbart_red_edge_3']
    del nci_dataset['image']['bands']['nbart_swir_2']
    del nci_dataset['image']['bands']['nbart_swir_3']
    del nci_dataset['lineage']
    nci_dataset['creation_dt'] = nci_dataset['extent']['center_dt']  # FIXME: WTF
    nci_dataset['product_type'] = 'S2MSIARD_NBAR'
    nci_dataset['original_id'] = nci_dataset['id']
    nci_dataset['software_versions'].update({
        's2_to_s3_rolling': {  # FIXME: Update
            'repo': 'https://github.com/GeoscienceAustralia/dea-airflow/',
            'version': '1.0.0'}
    })

    # Create a deterministic dataset ID based on these inputs
    nci_dataset['id'] = str(odc_uuid("s2_to_s3_rolling", "1.0.0", [nci_dataset['id']]))
    return nci_dataset


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


if __name__ == '__main__':
    main()
