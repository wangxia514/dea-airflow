#!/usr/bin/env python3
"""
Script to sync Sentinel-2 data from NCI to AWS S3 bucket
"""

import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import as_completed
from odc.aws import s3_dump
from pathlib import Path
import os
import json
import boto3
import botocore
from eodatasets3 import DatasetAssembler
from eodatasets3.scripts.tostac import json_fallback
import datetime

import click
import yaml
from odc.aws import s3_client
from tqdm import tqdm
from eodatasets3.stac import to_stac_item
from eodatasets3.model import (
    DatasetDoc,
    ProductDoc,
    AccessoryDoc,
    Location,
)

import rasterio
from eodatasets3 import serialise, validate, images, documents
from rasterio import DatasetReader
from shapely.geometry.polygon import Polygon

NCI_DIR = '/g/data/if87/datacube/002/S2_MSI_ARD/packaged'
S3_PATH = 'L2/sentinel-2-nbart/S2MSIARD_NBART'
S3_BUCKET = 'dea-public-data-dev'
WORK_DIR = Path('/g/data/v10/work/s2_nbart_rolling_archive')

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
@click.argument('granule_ids', type=click.File('r'))
@click.option('--workers', type=int, default=10)
def main(granule_ids, workers):
    """
    Script to sync Sentinel-2 data from NCI to AWS S3 bucket
    Pass in a file containing destination S3 urls that need to be uploaded.
    """
    setup_logging()

    global S3
    S3 = s3_client()
    granule_ids = [granule_id.strip() for granule_id in granule_ids.readlines()]

    _LOG.info(f"{len(granule_ids)} datasets to upload.")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(upload_dataset, granule_id) for granule_id in granule_ids]

        for future in tqdm(as_completed(futures), total=len(granule_ids), unit='datasets', disable=None):
            _LOG.info(f"Completed uploaded: {future.result()}")


def upload_dataset(granule_id):
    """
    :param granule_id: the id of the granule in format 'date/tile_id'
    """
    session = boto3.session.Session()

    if not check_granule_uploaded(granule_id, session):
        upload_dataset_without_yaml(granule_id)
        stac = upload_metadata(granule_id)
        send_stac_sns(stac, session)


def check_granule_uploaded(granule_id, session):
    """
    Checks to see whether the folder `granule_id` exists

    :param granule_id: the id of the granule in format 'date/tile_id'
    :param session: boto3 Session object
    :return: bool - `True` indicates that ganule has been uploaded
    """
    s3 = session.resource('s3')
    try:
        _ = s3.Object(S3_BUCKET, f"{S3_PATH}/{granule_id}/stac-ARD-METADATA.json").load()
        _LOG.info(f"{granule_id} already uploaded. Skipping.")
        return True
    except botocore.exceptions.ClientError:
        return False



def upload_dataset_without_yaml(granule_id):
    """
    Run AWS sync command to sync granules to S3 bucket
    :param granule_id: the id of the granule in format 'date/tile_id'
    :param _s3_bucket: name of the s3 bucket
    """
    local_path = Path(NCI_DIR) / granule_id
    s3_path = f"s3://{S3_BUCKET}/{S3_PATH}/{granule_id}"

    # Remove any data that shouldn't be there and exclude the metadata and NBAR
    command = f"aws s3 sync {local_path} {s3_path} " \
              "--only-show-errors " \
              "--delete " \
              "--exclude NBAR/* " \
              "--exclude ARD-METADATA.yaml " \
              "--exclude *NBAR_CONTIGUITY.TIF"

    try:
        subprocess.run(command, shell=True, check=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        _LOG.info(f"Upload failed, stdout: {e.stdout}, stderr: {e.stderr}")
        raise e


def upload_metadata(granule_id):
    """
    Creates and uploads metadata in stac and eo3 formats.
    :param granule_id: the id of the granule in format 'date/tile_id'
    :return: serialized stac metadata
    """

    local_path = Path(NCI_DIR) / granule_id

    s3_path = f"s3://{S3_BUCKET}/{S3_PATH}/{granule_id}/"
    s3_path_eo3 = f"{s3_path}eo3-ARD-METADATA.yaml"
    s3_path_stac = f"{s3_path}stac-ARD-METADATA.json"

    eo3 = create_eo3(local_path)
    stac = to_stac_item(
        eo3,
        stac_item_destination_url=s3_path_stac,
        odc_dataset_metadata_url=s3_path_eo3,
        dataset_location=s3_path,
    )
    stac = json.dumps(stac, default=json_fallback, indent=4)

    s3_dump(yaml.safe_dump(serialise.to_doc(eo3), default_flow_style=False), s3_path_eo3, S3)
    s3_dump(stac, s3_path_stac, S3)

    return stac


def send_stac_sns(stac, session):
    """
    Sends stac metadata as an SNS message

    :param stac: serialized stac metadata
    :param session: boto3 Session object
    """

    resource = session.client('sns', region_name='ap-southeast-2')
    resource.publish(
        TopicArn="arn:aws:sns:ap-southeast-2:451924316694:U29500-Test",
        Message=json.dumps({'default': stac}),
        MessageStructure='json'
    )


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


code_to_band = {
    "B01": 'nbart_coastal_aerosol', "B02": 'nbart_blue',
    "B03": 'nbart_green', "B04": 'nbart_red',
    "B05": 'nbart_red_edge_1', "B06": 'nbart_red_edge_2',
    "B07": 'nbart_red_edge_3', "B08": 'nbart_nir_1',
    "B11": 'nbart_swir_2', "B12": 'nbart_swir_3',
    "B8A": 'nbart_nir_2'
}


def add_to_eo3(assembler, dataset_dir, folder, func, expand_valid_data):
    """
    Helper function to add measurements to the DatasetAssembler

    :param assembler: the DatasetAssembler
    :param dataset_dir (Path): the firectory of the dataset
    :param folder (str): the subfolder containing the measurement bands
    :param func: a function that transforms file names to the correct band name
    """
    fns = [os.path.join(folder, fn) for fn in os.listdir(dataset_dir / folder) if fn[-3:] == "TIF"]
    fns = [fn for fn in fns if "QUICKLOOK" not in fn]
    for i, fn in enumerate(fns):
        name = func(fn.split('.')[-2])
        note_measurement(
            assembler, name, fn, relative_to_dataset_location=True, expand_valid_data=expand_valid_data
        )


def add_datetime(assembler, dataset_dir):
    """
    Adds the datetime from the original eo metadata.
    """
    eo_path = dataset_dir / "ARD-METADATA.yaml"
    with open(eo_path) as fin:
        eo = yaml.safe_load(fin)
    assembler.datetime = datetime.datetime.strptime(eo['extent']['center_dt'], '%Y-%m-%dT%H:%M:%S.%fZ')


def create_eo3(dataset_dir):
    """
    Creates an eo3 dataset document.

    :param dataset_dir (Path): the dataset directory
    :return: DatasetDoc of eo3 metadata
    """

    with open(dataset_dir / "ARD-METADATA.yaml") as fin:
        metadata = yaml.safe_load(fin)

    try:
        coords = metadata['grid_spatial']['projection']['valid_data']['coordinates']
        expand_valid_data = False
    except KeyError:
        expand_valid_data = True

    assembler = DatasetAssembler(
            dataset_location=dataset_dir,
            metadata_path=dataset_dir / "dummy",
    )

    if "S2A" in str(dataset_dir):
        assembler.product_family = "s2a_ard_granule"
    else:
        assembler.product_family = "s2b_ard_granule"

    assembler.processed_now()

    add_datetime(assembler, dataset_dir)
    add_to_eo3(assembler, dataset_dir, "NBART", lambda x: code_to_band[x.split('_')[-1]], expand_valid_data)
    add_to_eo3(assembler, dataset_dir, "SUPPLEMENTARY", lambda x: x[3:].lower(), expand_valid_data)
    add_to_eo3(assembler, dataset_dir, "QA", lambda x: x[3:].lower().replace('combined_', ''), expand_valid_data)

    crs, grid_docs, measurement_docs = assembler._measurements.as_geo_docs()
    valid_data = assembler._measurements.consume_and_get_valid_data()

    dataset = DatasetDoc(
        id=assembler.dataset_id,
        label=assembler.label,
        product=ProductDoc(
            name=assembler.names.product_name, href=assembler.names.product_uri
        ),
        crs=assembler._crs_str(crs) if crs is not None else None,
        geometry=valid_data,
        grids=grid_docs,
        properties=assembler.properties,
        accessories={
            name: AccessoryDoc(path, name=name)
            for name, path in assembler._accessories.items()
        },
        measurements=measurement_docs,
        lineage=assembler._lineage,
    )

    if not expand_valid_data:
        dataset.geometry = Polygon(coords[0])

    return dataset


def note_measurement(
    assembler,
    name,
    path: Location,
    expand_valid_data=True,
    relative_to_dataset_location=False,
):
    """
    Reference a measurement from its existing file path.

    (no data is copied, but Geo information is read from it.)

    :param name:
    :param path:
    :param expand_valid_data:
    :param relative_to_dataset_location:
    """
    read_location = path
    if relative_to_dataset_location:
        read_location = documents.resolve_absolute_offset(
            assembler._dataset_location
            or (assembler._metadata_path and assembler._metadata_path.parent),
            path,
        )
    with rasterio.open(read_location) as ds:
        ds: DatasetReader
        if ds.count != 1:
            raise NotImplementedError(
                "TODO: Only single-band files currently supported"
            )

        assembler._measurements.record_image(
            name,
            images.GridSpec.from_rio(ds),
            path,
            ds.read(1) if expand_valid_data else None,
            nodata=ds.nodata,
            expand_valid_data=expand_valid_data,
        )


if __name__ == '__main__':
    main()

