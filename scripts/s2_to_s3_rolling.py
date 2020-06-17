#!/usr/bin/env python3
"""
Script to sync Sentinel-2 data from NCI to AWS S3 bucket
"""

from datetime import datetime as dt, timedelta
from pathlib import Path
import logging
import subprocess

import click
import boto3
import botocore
import yaml
from odc.index import odc_uuid

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
LOG = logging.getLogger("s3_to_s3_rolling")
LOG.setLevel(logging.DEBUG)
LOG.addHandler(handler)


NCI_DIR = '/g/data/if87/datacube/002/S2_MSI_ARD/packaged'
S3_PATH = 'L2/sentinel-2-nbar/S2MSIARD_NBAR'


def find_granules(_num_days, _end_date, root_path=NCI_DIR):
    """
    Find granules for the date range specified above. Format is yyyy-mm-dd/granule
    :param _num_days: Number of days to process before the end date.
    :param _end_date: End date for processing granules.
    :param root_path: Root path of Sentinel-2 Data in NCI
    :return: List of granules
    """
    # Find the dates between the input date and today, inclusive, formatted like the directories
    dates = [(_end_date - timedelta(days=x)
              ).strftime("%Y-%m-%d") for x in range(_num_days + 1)]

    # The list of folders will be returned and will contain all the granules available for
    # the date range specified above. Format is yyyy-mm-dd/granule
    list_of_granules = []

    for date in dates:
        dir_for_date = Path(root_path).joinpath(date)
        if Path(dir_for_date).exists():
            granules = [date + "/" + name.name for name in Path(dir_for_date).iterdir()]
            list_of_granules += granules

    return list_of_granules


def check_granule_exists(_s3_bucket, s3_metadata_path):
    """
    Check if granaule already exists in S3 bucket
    :param _s3_bucket: name of s3 bucket to store granules
    :param s3_metadata_path: Path of metadata file
    :return:
    """
    s3_resource = boto3.resource('s3')

    try:
        # This does a head request, so is fast
        s3_resource.Object(_s3_bucket, s3_metadata_path).load()
    except botocore.exceptions.ClientError as exception:
        if exception.response['Error']['Code'] == "404":
            return False
    else:
        return True


def sync_granule(granule, _s3_bucket):
    """
    Run AWS sync command to sync granules to S3 bucket
    :param granule: name of the granule
    :param _s3_bucket: name of the s3 bucket
    :return: Returns code zero, if success.
    """
    local_path = Path(NCI_DIR).joinpath(granule)
    s3_path = "s3://{s3_bucket}/{s3_path}/{granule}".format(
        s3_bucket=_s3_bucket,
        s3_path=S3_PATH,
        granule=granule
    )

    # Remove any data that shouldn't be there and exclude the metadata and NBART
    command = "aws s3 sync {local_path} {s3_path} " \
              "--no-progress " \
              "--delete " \
              "--exclude NBART/* " \
              "--exclude ARD-METADATA.yaml".format(local_path=local_path, s3_path=s3_path)

    return_code = subprocess.call(command, shell=True)

    if return_code == 0:
        LOG.info("Finished processing of granule -  %s", granule)
    else:
        LOG.info("Failed processing of granule - %s", granule)

    # If the return code is zero, we have success.
    return return_code == 0


def replace_metadata(yaml_file, _s3_bucket, s3_metadata_path):
    """
    Replace metadata with additional info
    :param yaml_file: metadata file in NCI
    :param _s3_bucket: name of s3 bucket
    :param s3_metadata_path: path of metadata file in s3
    """
    s3_resource = boto3.resource("s3").Bucket(_s3_bucket)

    with open(yaml_file) as config_file:
        temp_metadata = yaml.load(config_file, Loader=yaml.CSafeLoader)

    del temp_metadata['image']['bands']['nbart_blue']
    del temp_metadata['image']['bands']['nbart_coastal_aerosol']
    del temp_metadata['image']['bands']['nbart_contiguity']
    del temp_metadata['image']['bands']['nbart_green']
    del temp_metadata['image']['bands']['nbart_nir_1']
    del temp_metadata['image']['bands']['nbart_nir_2']
    del temp_metadata['image']['bands']['nbart_red']
    del temp_metadata['image']['bands']['nbart_red_edge_1']
    del temp_metadata['image']['bands']['nbart_red_edge_2']
    del temp_metadata['image']['bands']['nbart_red_edge_3']
    del temp_metadata['image']['bands']['nbart_swir_2']
    del temp_metadata['image']['bands']['nbart_swir_3']
    del temp_metadata['lineage']
    temp_metadata['creation_dt'] = temp_metadata['extent']['center_dt']
    temp_metadata['product_type'] = 'S2MSIARD_NBAR'
    temp_metadata['original_id'] = temp_metadata['id']
    temp_metadata['software_versions'].update({
        's2_to_s3_rolling': {
            'repo': 'https://github.com/GeoscienceAustralia/dea-airflow/',
            'version': '1.0.0'}
    })

    # Create dataset ID based on Kirill's magic
    temp_metadata['id'] = str(odc_uuid("s2_to_s3_rolling", "1.0.0", [temp_metadata['id']]))

    # Write to S3 directly
    s3_resource.Object(key=s3_metadata_path).put(
        Body=yaml.dump(temp_metadata, default_flow_style=False, Dumper=yaml.CSafeDumper)
    )

    LOG.info("Finished uploaded metadata %s to %s", yaml_file, s3_metadata_path)


def sync_dates(_num_days, _end_date, _s3_bucket, _update='no'):
    """
    Sync granules to S3 bucket for specified dates
    :param _num_days: Number of days to process before the end date.
    :param _end_date: End date for processing granules.
    :param _s3_bucket: Name of the S3 bucket
    :param _update: Option for granule/metadata update
    ('granule_metadata' or 'granule' or 'metadata' or 'no')
    """
    # Since all file paths are of the form:
    # /g/data/if87/datacube/002/S2_MSI_ARD/packaged/YYYY-mm-dd/<granule>
    # we can simply list all the granules per date and sync them
    datetime_end = dt.today() if _end_date == 'today' else dt.strptime(_end_date, "%Y-%m-%d")

    # Get list of granules
    list_of_granules = find_granules(_num_days, datetime_end)
    LOG.info("Found %s files to process", len(list_of_granules))

    # For each granule, sync it if it needs syncing
    if len(list_of_granules) > 0:
        for granule in list_of_granules:
            LOG.info("Processing %s", granule)

            yaml_file = "{nci_path}/{granule}/ARD-METADATA.yaml".format(
                nci_path=NCI_DIR,
                granule=granule
            )
            # Checking if metadata file exists
            if Path(yaml_file).exists():
                # s3://dea-public-data
                # /L2/sentinel-2-nbar/S2MSIARD_NBAR/2017-07-02
                # /S2A_OPER_MSI_ARD_TL_SGS__20170702T022539_A010581_T54LTL_N02.05
                # /ARD-METADATA.yaml
                s3_metadata_path = "{s3_path}/{granule}/ARD-METADATA.yaml".format(
                    s3_path=S3_PATH,
                    granule=granule
                )

                already_processed = check_granule_exists(_s3_bucket, s3_metadata_path)

                # Maybe todo: include a flag to force replace
                # Check if already processed and apply sync action accordingly
                sync_action = 'granule_metadata' if not already_processed else _update

                if sync_action != 'no':
                    if sync_action in ('granule_metadata', 'granule'):
                        sync_success = sync_granule(granule, _s3_bucket)
                    else:
                        sync_success = True

                    if sync_success and (sync_action in ('metadata', 'granule_metadata')):
                        # Replace the metadata with a deterministic ID
                        replace_metadata(yaml_file, _s3_bucket, s3_metadata_path)
                        LOG.info("Finished processing and/or uploaded metadata to %s",
                                 s3_metadata_path)
                    else:
                        LOG.error("Failed to sync data... skipping")
                        raise ValueError("Failed to sync data... skipping")
                else:
                    LOG.warning("Metadata exists, not syncing %s", granule)
            else:
                LOG.error("Metadata is missing, not syncing %s", granule)
                raise ValueError("Metadata is missing, not syncing %s", granule)
    else:
        LOG.warning("Didn't find any granules to process...")


@click.command()
@click.option("--numdays", '-n', type=int, required=True)
@click.option("--enddate", '-d', type=str, required=True)
@click.option("--s3bucket", '-b', type=str, required=True)
@click.option('--doupdate', '-u',
              type=click.Choice(['granule_metadata', 'granule', 'metadata', 'no'], case_sensitive=True),
              default='no')
def main(numdays, enddate, s3bucket, doupdate):
    """
    Script to sync Sentinel-2 data from NCI to AWS S3 bucket
    :param numdays: Number of days to process before the end date.
    :param enddate: End date for processing granules.
    :param s3bucket: Name of the S3 bucket
    :param doupdate: Option for granule/metadata update
    """
    sync_dates(numdays, enddate, s3bucket, doupdate)
    LOG.info("Syncing %s days back from %s into the %s bucket and update is %s",
             numdays, enddate, s3bucket, doupdate)


if __name__ == '__main__':
    main()
