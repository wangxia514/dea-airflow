#!/usr/bin/env python3
"""
Script to sync Sentinel-2 data from NCI to AWS S3 bucket
"""

import datetime
import json
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import as_completed
from pathlib import Path

import boto3
import botocore
import click
import rasterio
import yaml
from rasterio import DatasetReader
from shapely.geometry.polygon import Polygon
from tqdm import tqdm

from eodatasets3 import DatasetAssembler, documents, images, serialise, validate
from eodatasets3.model import AccessoryDoc, DatasetDoc, Location, ProductDoc
from eodatasets3.scripts.tostac import json_fallback
from eodatasets3.stac import to_stac_item
from odc.aws import s3_client, s3_dump

from c3_to_s3_rolling import (
    check_granule_exists,
    publish_sns,
    get_common_message_attributes,
    sync_granule
)

NCI_DIR = '/g/data/if87/datacube/002/S2_MSI_ARD/packaged'
S3_BUCKET = "dea-public-data"
WORK_DIR = Path("/g/data/v10/work/s2_nbart_rolling_archive")
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
@click.argument('sns_topic_arn', type=str)
@click.option('--workers', type=int, default=10)
def main(granule_ids, sns_topic_arn, workers):
    """
    Script to sync Sentinel-2 data from NCI to AWS S3 bucket
    Pass in a file containing destination S3 urls that need to be uploaded.
    """

    setup_logging()

    granule_ids = [granule_id.strip() for granule_id in granule_ids.readlines()]

    _LOG.info(f"{len(granule_ids)} granules to upload.")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(upload_granule, granule_id, sns_topic_arn) for granule_id in granule_ids]

        for future in tqdm(as_completed(futures), total=len(granule_ids), unit='granules', disable=None):
            _LOG.info(f"Completed uploaded: {future.result()}")


def upload_granule(granule_id, sns_topic_arn):
    """
    :param granule_id: the id of the granule in format 'date/tile_id'
    """
    session = boto3.session.Session()
    bucket_stac_path = f"{get_granule_s3_path(granule_id)}/stac-ARD-METADATA.json"

    if not check_granule_exists(S3_BUCKET, bucket_stac_path, session=session):
        sync_granule(
            granule_id,
            NCI_DIR,
            Path(get_granule_s3_path(granule_id)).parent.parent,
            S3_BUCKET,
            exclude=["NBAR/*", "ARD-METADATA.yaml", "*NBAR_CONTIGUITY.TIF"],
            cross_account=True,
        )

        stac_dump, s3_stac_path = upload_metadata(granule_id)

        message_attributes = get_common_message_attributes(json.loads(stac_dump))
        message_attributes.update(
            {"action": {"DataType": "String", "StringValue": "ADDED"}}
        )

        _LOG.info(f"Sending SNS. Granule id: {granule_id}")
        try:
            publish_sns(sns_topic_arn, stac_dump, message_attributes, session=session)
        except Exception as e:
            _LOG.info(f"SNS send failed: {e}. Granule id: {granule_id}")

        _LOG.info(f"Uploading STAC: {granule_id}")
        s3_dump(stac_dump, s3_stac_path, ACL="bucket-owner-full-control", ContentType="application/json")  # upload STAC last
    else:
        _LOG.info(f"Granule {granule_id} already uploaded, skipping.")


def get_granule_s3_path(granule_id):

    if "S2A" in granule_id:
        granule_s3_path = f"baseline/s2a_ard_granule/{granule_id}"
    elif "S2B" in granule_id:
        granule_s3_path = f"baseline/s2b_ard_granule/{granule_id}"
    else:
        raise ValueError(f"granule_id: must contain 'S2A' or S2B, found {granule_id}.")

    return granule_s3_path


def upload_metadata(granule_id):
    """
    Creates and uploads metadata in stac and eo3 formats.
    :param granule_id: the id of the granule in format 'date/tile_id'
    :return: serialized stac metadata
    """

    local_path = Path(NCI_DIR) / granule_id
    granule_s3_path = get_granule_s3_path(granule_id)

    s3_path = f"s3://{S3_BUCKET}/{granule_s3_path}/"
    s3_eo3_path = f"{s3_path}eo3-ARD-METADATA.yaml"
    s3_stac_path = f"{s3_path}stac-ARD-METADATA.json"

    eo3 = create_eo3(local_path, granule_id)
    stac = to_stac_item(
        eo3,
        stac_item_destination_url=s3_stac_path,
        odc_dataset_metadata_url=s3_eo3_path,
        dataset_location=s3_path,
    )
    stac_dump = json.dumps(stac, default=json_fallback, indent=4)

    s3_dump(
        yaml.safe_dump(serialise.to_doc(eo3), default_flow_style=False), 
        s3_eo3_path, 
        ACL="bucket-owner-full-control",
        ContentType="text/vnd.yaml"
    )

    return stac_dump, s3_stac_path


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


def add_to_eo3(assembler, granule_dir, folder, func, expand_valid_data):
    """
    Helper function to add measurements to the DatasetAssembler

    :param assembler: the DatasetAssembler
    :param granule_dir (Path): the firectory of the granule
    :param folder (str): the subfolder containing the measurement bands
    :param func: a function that transforms file names to the correct band name
    """
    fns = [os.path.join(folder, fn) for fn in os.listdir(granule_dir / folder) if fn[-3:] == "TIF"]
    fns = [fn for fn in fns if "QUICKLOOK" not in fn]
    for i, fn in enumerate(fns):
        name = func(fn.split('.')[-2])
        assembler.note_measurement(
            name, fn, relative_to_dataset_location=True, expand_valid_data=expand_valid_data
        )


def add_datetime(assembler, granule_dir):
    """
    Adds the datetime from the original eo metadata.
    """
    eo_path = granule_dir / "ARD-METADATA.yaml"
    with open(eo_path) as fin:
        eo = yaml.safe_load(fin)
    assembler.datetime = datetime.datetime.strptime(eo['extent']['center_dt'], '%Y-%m-%dT%H:%M:%S.%fZ')


def create_eo3(granule_dir, granule_id):
    """
    Creates an eo3 document.

    :param granule_dir (Path): the granule directory
    :return: DatasetDoc of eo3 metadata
    """

    with open(granule_dir / "ARD-METADATA.yaml") as fin:
        metadata = yaml.safe_load(fin)

    try:
        coords = metadata['grid_spatial']['projection']['valid_data']['coordinates']
        expand_valid_data = False
    except KeyError:
        expand_valid_data = True

    assembler = DatasetAssembler(
            dataset_location=granule_dir,
            metadata_path=granule_dir / "dummy",
    )

    if "S2A" in str(granule_dir):
        assembler.product_family = "s2a_ard_granule"
        platform = "SENTINEL_2A"        
    else:
        assembler.product_family = "s2b_ard_granule"
        platform = "SENTINEL_2B"

    assembler.processed_now()

    add_datetime(assembler, granule_dir)
    add_to_eo3(assembler, granule_dir, "NBART", lambda x: code_to_band[x.split('_')[-1]], expand_valid_data)
    add_to_eo3(assembler, granule_dir, "SUPPLEMENTARY", lambda x: x[3:].lower(), expand_valid_data)
    add_to_eo3(assembler, granule_dir, "QA", lambda x: x[3:].lower().replace('combined_', ''), expand_valid_data)

    crs, grid_docs, measurement_docs = assembler._measurements.as_geo_docs()
    valid_data = assembler._measurements.consume_and_get_valid_data()

    assembler.properties["odc:region_code"] = metadata["provider"]["reference_code"]
    assembler.properties["gqa:cep90"] = metadata["gqa"]["residual"]["cep90"]
    assembler.properties["gqa:error_message"] = metadata["gqa"]["error_message"]
    assembler.properties["gqa:final_gcp_count"] =metadata["gqa"]["final_gcp_count"]
    assembler.properties["gqa:ref_source"] = metadata["gqa"]["ref_source"]
    assembler.properties["sentinel:datatake_start_datetime"] = granule_id.split("_")[-4]
    assembler.properties["eo:platform"] = platform
    assembler.properties["eo:instrument"] = "MSI"

    for key in ["abs_iterative_mean", "abs", "iterative_mean", "iterative_stddev", "mean", "stddev"]:
        assembler.properties[f"gqa:{key}_xy"] = metadata["gqa"]["residual"][key]["xy"]

    eo3 = DatasetDoc(
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
        eo3.geometry = Polygon(coords[0])

    for measurement in eo3.measurements.values():
        if measurement.grid is None:
            measurement.grid = 'default'

    return eo3


if __name__ == '__main__':
    main()
