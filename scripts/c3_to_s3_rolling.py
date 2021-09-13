#!/usr/bin/env python3
"""
Script to sync Collection 3 data from NCI to AWS S3 bucket
"""
import math

import csv
import io
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict
from toolz import dicttoolz

from botocore.exceptions import ClientError
import boto3
import click

from eodatasets3 import verify, serialise
from eodatasets3.scripts.tostac import dc_to_stac, json_fallback

LOG = logging.getLogger("c3_to_s3_rolling")


def find_granules(file_path):
    """
    Load a list of metadata files in NCI

    :param file_path: File with metadata list
    :return: List of granules
    """
    with open(file_path, "r") as f:
        return [row for row in csv.reader(f)]


def check_granule_exists(_s3_bucket, s3_metadata_path, session=None):
    """
    Check if granaule already exists in S3 bucket

    :param _s3_bucket: Name of s3 bucket to store granules
    :param s3_metadata_path: Path of metadata file
    :param session: boto3 Session object
    :return: True if success else False
    """
    if session is None:
        s3_resource = boto3.resource("s3")
    else:
        s3_resource = session.resource("s3")

    try:
        # This does a head request, so is fast
        s3_resource.Object(_s3_bucket, s3_metadata_path).load()
    except ClientError as exception:
        if exception.response["Error"]["Code"] == "404":
            return False
    else:
        return True


def upload_s3_resource(
    s3_bucket, s3_file, obj, session=None, content_type="binary/octet-stream"
):
    """
    Upload s3 resource object in provided s3 path

    :param s3_bucket: Name of s3 bucket to store granules
    :param s3_file: Path of metadata file
    :param obj: Resource object to upload
    :param session: boto3 Session object
    """
    try:
        if session is None:
            s3_resource = boto3.resource("s3").Bucket(s3_bucket)
        else:
            s3_resource = session.resource("s3").Bucket(s3_bucket)
        s3_resource.Object(key=s3_file).put(Body=obj, ContentType=content_type)
    except ValueError as exception:
        raise S3SyncException(str(exception))
    except ClientError as exception:
        raise S3SyncException(str(exception))


def load_s3_resource(s3_bucket, s3_file):
    """
    Download S3 resource object in provided s3 path

    :param s3_bucket: Name of s3 bucket
    :param s3_file: Path of file in S3
    :return obj: Resource object to download
    """
    try:
        s3_resource = boto3.resource("s3").Bucket(s3_bucket)
        obj = s3_resource.Object(key=s3_file)
        return obj.get()["Body"]
    except ValueError as exception:
        raise S3SyncException(str(exception))
    except ClientError as exception:
        raise S3SyncException(str(exception))


def publish_sns(sns_topic, message, message_attributes, session=None):
    """
    Publish message containing STAC metadata to SNS Topic

    :param sns_topic: ARN of the SNS Topic
    :param message: SNS message
    :param message_attributes: SNS message attributes
    :param session: boto3 Session object
    """
    try:
        if session is None:
            sns_client = boto3.client("sns")
        else:
            sns_client = session.client("sns")
        sns_client.publish(
            TopicArn=sns_topic, Message=message, MessageAttributes=message_attributes
        )
    except ClientError as exception:
        raise S3SyncException(str(exception))


def upload_checksum(
    nci_metadata_file_path,
    checksum_file_path,
    new_checksum_list,
    s3_bucket,
    s3_path,
    session=None,
    excluded_pattern=["ga_*_nbar_*.*"],
):
    """
    Updates and uploads checksum file

    :param nci_metadata_file_path: Path of metadata file
    :param checksum_file_path: Path of checksum file
    :param new_checksum_list: List of filename and updated checksum
    :param s3_bucket: Name of the S3 bucket
    :param s3_path: Path of the S3 bucket
    :param session: boto3 Session object
    :param excluded_pattern: a list of file patterns to exclude from the checksum
    """

    # Identify list of files to be included in checksum file
    excluded_files = []
    excluded_pattern.extend(
        [
            nci_metadata_file_path.name,
            checksum_file_path.name,
        ]
    )

    for ex_pat in excluded_pattern:
        for path in checksum_file_path.parent.glob(ex_pat):
            excluded_files.append(path.name)

    # Read checksum for files to be included
    with checksum_file_path.open("r") as f:
        for hash_, filename in [line.strip().split("\t") for line in f.readlines()]:
            if filename not in excluded_files:
                new_checksum_list[filename] = hash_

    # Write checksum to buffer
    with io.BytesIO() as temp_checksum:
        temp_checksum.writelines(
            f"{str(hash_)}\t{str(filename)}\n".encode("utf-8")
            for filename, hash_ in sorted(new_checksum_list.items())
        )

        # Write checksum sha1 object into S3
        s3_checksum_file = f"{s3_path}/{checksum_file_path.name}"
        upload_s3_resource(
            s3_bucket,
            s3_checksum_file,
            temp_checksum.getvalue(),
            session=session,
            content_type="text/plain",
        )


def get_common_message_attributes(stac_doc: Dict) -> Dict:
    """
    Returns common message attributes dict
    :param stac_doc: STAC dict
    :return: common message attributes dict
    """
    msg_attributes = {}

    product = dicttoolz.get_in(["properties", "odc:product"], stac_doc)
    if product:
        msg_attributes["product"] = {
            "DataType": "String",
            "StringValue": product,
        }

    datetime = dicttoolz.get_in(["properties", "datetime"], stac_doc)
    if datetime:
        msg_attributes["datetime"] = {
            "DataType": "String",
            "StringValue": datetime,
        }

    cloudcover = dicttoolz.get_in(["properties", "eo:cloud_cover"], stac_doc)
    if cloudcover:
        msg_attributes["cloudcover"] = {
            "DataType": "Number",
            "StringValue": str(cloudcover),
        }

    maturity = dicttoolz.get_in(["properties", "dea:dataset_maturity"], stac_doc)
    if maturity:
        msg_attributes["maturity"] = {
            "DataType": "String",
            "StringValue": maturity,
        }

    bbox = dicttoolz.get_in(["bbox"], stac_doc)
    if bbox and len(bbox) > 3:
        msg_attributes["bbox.ll_lon"] = {
            "DataType": "Number",
            "StringValue": str(bbox[0]),
        }
        msg_attributes["bbox.ll_lat"] = {
            "DataType": "Number",
            "StringValue": str(bbox[1]),
        }
        msg_attributes["bbox.ur_lon"] = {
            "DataType": "Number",
            "StringValue": str(bbox[2]),
        }
        msg_attributes["bbox.ur_lat"] = {
            "DataType": "Number",
            "StringValue": str(bbox[3]),
        }

    gqa_iterative_mean_xy = dicttoolz.get_in(
        ["properties", "gqa:iterative_mean_xy"], stac_doc
    )
    if gqa_iterative_mean_xy and not math.isnan(gqa_iterative_mean_xy):
        msg_attributes["gqa_iterative_mean_xy"] = {
            "DataType": "Number",
            "StringValue": str(gqa_iterative_mean_xy),
        }

    return msg_attributes


def update_metadata(
    nci_metadata_file, s3_bucket, s3_base_url, explorer_base_url, sns_topic, s3_path
):
    """
    Uploads updated metadata with nbar element removed, updated checksum file, STAC doc created
    and publish SNS message

    :param nci_metadata_file: Path of metadata file in NCI
    :param s3_bucket: Name of S3 bucket
    :param s3_base_url: Base URL of the S3 bucket
    :param explorer_base_url: Base URL of the explorer
    :param sns_topic: ARN of the SNS topic
    :param s3_path: Path in S3
    :return: List of errors
    """
    # Initialise error list
    metadata_error_list = []
    # Initialise checksum list
    new_checksum_list = {}

    nci_metadata_file_path = Path(nci_metadata_file)
    temp_metadata = serialise.load_yaml(nci_metadata_file_path)

    # Deleting Nbar related metadata
    # Because Landsat 8 is different, we need to check if the fields exist
    # before removing them.
    if "nbar_blue" in temp_metadata["measurements"]:
        del temp_metadata["measurements"]["nbar_blue"]
    if "nbar_green" in temp_metadata["measurements"]:
        del temp_metadata["measurements"]["nbar_green"]
    if "nbar_nir" in temp_metadata["measurements"]:
        del temp_metadata["measurements"]["nbar_nir"]
    if "nbar_red" in temp_metadata["measurements"]:
        del temp_metadata["measurements"]["nbar_red"]
    if "nbar_swir_1" in temp_metadata["measurements"]:
        del temp_metadata["measurements"]["nbar_swir_1"]
    if "nbar_swir_2" in temp_metadata["measurements"]:
        del temp_metadata["measurements"]["nbar_swir_2"]
    if "nbar_coastal_aerosol" in temp_metadata["measurements"]:
        del temp_metadata["measurements"]["nbar_coastal_aerosol"]
    if "nbar_panchromatic" in temp_metadata["measurements"]:
        del temp_metadata["measurements"]["nbar_panchromatic"]
    if "oa_nbar_contiguity" in temp_metadata["measurements"]:
        del temp_metadata["measurements"]["oa_nbar_contiguity"]
    if "thumbnail:nbar" in temp_metadata["accessories"]:
        del temp_metadata["accessories"]["thumbnail:nbar"]

    # Format an eo3 dataset dict for human-readable yaml serialisation.
    temp_metadata = serialise.prepare_formatting(temp_metadata)

    # Dump metadata yaml into buffer
    with io.BytesIO() as temp_yaml:
        serialise.dumps_yaml(temp_yaml, temp_metadata)
        temp_yaml.seek(
            0
        )  # Seek back to the beginning of the file before next read/write
        new_checksum_list[nci_metadata_file_path.name] = verify.calculate_hash(
            temp_yaml
        )

        # Write odc metadata yaml object into S3
        s3_metadata_file = f"{s3_path}/{nci_metadata_file_path.name}"
        try:
            upload_s3_resource(
                s3_bucket,
                s3_metadata_file,
                temp_yaml.getvalue(),
                content_type="text/vnd.yaml",
            )
            LOG.info(f"Finished uploading metadata to {s3_metadata_file}")
        except S3SyncException as exp:
            LOG.error(f"Failed uploading metadata to {s3_metadata_file} - {exp}")
            metadata_error_list.append(
                f"Failed uploading metadata to {s3_metadata_file} - {exp}"
            )

    # Create stac metadata
    name = nci_metadata_file_path.stem.replace(".odc-metadata", "")
    stac_output_file_path = nci_metadata_file_path.with_name(f"{name}.stac-item.json")
    stac_url_path = f"{s3_base_url if s3_base_url else boto3.client('s3').meta.endpoint_url}/{s3_path}/"
    item_doc = dc_to_stac(
        serialise.from_doc(temp_metadata),
        nci_metadata_file_path,
        stac_output_file_path,
        stac_url_path,
        explorer_base_url,
        True,
    )
    stac_dump = json.dumps(item_doc, indent=4, default=json_fallback)

    # Write stac json to buffer
    with io.BytesIO() as temp_stac:
        temp_stac.write(stac_dump.encode())
        temp_stac.seek(
            0
        )  # Seek back to the beginning of the file before next read/write
        new_checksum_list[stac_output_file_path.name] = verify.calculate_hash(temp_stac)

        # Write stac metadata json object into S3
        s3_stac_file = f"{s3_path}/{stac_output_file_path.name}"
        try:
            upload_s3_resource(
                s3_bucket,
                s3_stac_file,
                temp_stac.getvalue(),
                content_type="application/json",
            )
            LOG.info(f"Finished uploading STAC metadata to {s3_stac_file}")
        except S3SyncException as exp:
            LOG.error(f"Failed uploading STAC metadata to {s3_stac_file} - {exp}")
            metadata_error_list.append(
                f"Failed uploading STAC metadata to {s3_stac_file} - {exp}"
            )

    # Publish message containing STAC metadata to SNS Topic
    message_attributes = get_common_message_attributes(json.loads(stac_dump))
    message_attributes.update(
        {"action": {"DataType": "String", "StringValue": "ADDED"}}
    )
    try:
        publish_sns(sns_topic, stac_dump, message_attributes)
        LOG.info(f"Finished publishing SNS Message to SNS Topic {sns_topic}")
    except S3SyncException as exp:
        LOG.error(f"Failed publishing SNS Message to SNS Topic {sns_topic} - {exp}")
        metadata_error_list.append(
            f"Failed publishing SNS Message to SNS Topic {sns_topic} - {exp}"
        )

    # Update checksum file
    checksum_filename = nci_metadata_file_path.stem.replace(".odc-metadata", "")
    checksum_file_path = nci_metadata_file_path.with_name(f"{checksum_filename}.sha1")
    try:
        upload_checksum(
            nci_metadata_file_path,
            checksum_file_path,
            new_checksum_list,
            s3_bucket,
            s3_path,
        )
        LOG.info(
            f"Finished uploading checksum file " f"{s3_path}/{checksum_file_path.name}"
        )
    except S3SyncException as exp:
        LOG.error(
            f"Failed uploading checksum file "
            f"{s3_path}/{checksum_file_path.name} - {exp}"
        )
        metadata_error_list.append(
            f"Failed uploading checksum file "
            f"{s3_path}/{checksum_file_path.name} - {exp}"
        )

    return metadata_error_list


def archive_granule(granule, s3_root_path, s3_bucket):
    """
    Run AWS rm command to delete granules from S3 bucket

    :param granule: Name of the granule
    :param s3_root_path: Root folder of the S3 bucket
    :param s3_bucket: Name of the S3 bucket
    :return: Returns code zero, if success.
    """
    s3_path = f"s3://{s3_bucket}/{s3_root_path}/{granule}"

    # Remove any data that shouldn't be there and exclude the metadata
    command = f"aws s3 rm {s3_path} --only-show-error --recursive "

    return_code = subprocess.call(command, shell=True)

    if return_code != 0:
        raise S3SyncException("Failed running S3 rm command")


def sync_granule(
    granule,
    nci_dir,
    s3_root_path,
    s3_bucket,
    exclude=["ga_*_nbar_*.*", "ga_*_nbar-*.*", "*.sha1"],
    cross_account=False,
):
    """
    Run AWS sync command to sync granules to S3 bucket

    :param granule: Name of the granule
    :param nci_dir: Source directory for the files in NCI
    :param s3_root_path: Root folder of the S3 bucket
    :param s3_bucket: Name of the S3 bucket
    :param exclude: list of file patterns to exclude
    :return: Returns code zero, if success.
    """
    local_path = Path(nci_dir).joinpath(granule)
    s3_path = f"s3://{s3_bucket}/{s3_root_path}/{granule}"

    # Remove any data that shouldn't be there and exclude the metadata
    exclude_string = ""
    if exclude:
        exclude_string = " ".join(f"--exclude {pattern}" for pattern in exclude)

    command = f"aws s3 sync {local_path} {s3_path} --only-show-errors {exclude_string}"
    if cross_account:
        command += " --acl bucket-owner-full-control"

    return_code = subprocess.call(command, shell=True)

    if return_code != 0:
        raise S3SyncException("Failed running S3 sync command. Return error code: " + return_code)


def sync_granules(
    file_path,
    nci_dir,
    s3_root_path,
    s3_bucket,
    s3_base_url,
    explorer_base_url,
    sns_topic,
    update=False,
):
    """
    Sync granules to S3 bucket for specified dates

    :param file_path: File path for the csv file listing scenes path
    :param nci_dir: Source directory for the files in NCI
    :param s3_root_path: Root folder of the S3 bucket
    :param s3_bucket: Name of the S3 bucket
    :param s3_base_url: Base URL of the S3 bucket
    :param explorer_base_url: Base URL of the Explorer
    :param sns_topic: ARN of the SNS topic
    :param update: Sets flag for a fresh sync of data and replace the metadata
    """
    # Initialise error list
    error_list = []

    # Get list of granules
    list_of_granules = find_granules(file_path)
    granules_count = len(list_of_granules)
    LOG.info(f"Found {granules_count} files to process")

    # For each granule, sync it if it needs syncing
    if granules_count > 0:
        for granule_row in list_of_granules:

            metadata_file = granule_row[0] if len(granule_row) > 0 else None
            is_archived = True if (len(granule_row) > 1 and granule_row[1]) else False
            action = "archived" if is_archived else "added"
            LOG.info(f"Processing {action} granule - {metadata_file} ")

            metadata_file_path = Path(metadata_file)
            granule = metadata_file_path.relative_to(nci_dir).parent
            metadata_file_name = metadata_file_path.name
            s3_path = f"{s3_root_path}/{granule}"
            s3_metadata_file = f"{s3_path}/{metadata_file_name}"
            s3_stac_file = f"{s3_path}/{metadata_file_path.stem.replace('.odc-metadata', '')}.stac-item.json"

            if is_archived:
                # Checks if metadata file exists in S3
                exists_in_s3 = check_granule_exists(s3_bucket, s3_metadata_file)
                if exists_in_s3:
                    try:
                        stac_dump = json.load(load_s3_resource(s3_bucket, s3_stac_file))

                        # Delete all files from the S3 path
                        archive_granule(granule, s3_root_path, s3_bucket)
                        LOG.info(f"Finished S3 archive of granule - {granule}")

                        # Publish message containing STAC metadata to SNS Topic
                        message_attributes = get_common_message_attributes(stac_dump)
                        message_attributes.update(
                            {
                                "action": {
                                    "DataType": "String",
                                    "StringValue": "ARCHIVED",
                                }
                            }
                        )
                        try:
                            publish_sns(
                                sns_topic, json.dumps(stac_dump), message_attributes
                            )
                            LOG.info(
                                f"Finished publishing SNS Message to SNS Topic {sns_topic}"
                            )
                        except S3SyncException as exp:
                            LOG.error(
                                f"Failed publishing SNS Message to SNS Topic {sns_topic} - {exp}"
                            )
                            error_list.append(
                                f"Failed publishing SNS Message to SNS Topic {sns_topic} - {exp}"
                            )

                    except S3SyncException as exp:
                        LOG.error(
                            f"Failed to archive {granule} "
                            f"because of an error in the rm command - {exp}"
                        )
                        error_list.append(
                            f"Failed to archive {granule} "
                            f"because of an error in the rm command - {exp}"
                        )
                else:
                    LOG.warning(
                        f"Metadata doesn't exists in S3, "
                        f"not deleting anything from S3 for {granule}"
                    )
            else:

                # Checking if metadata file exists
                if metadata_file_path.exists():
                    # s3://dea-public-data
                    # /analysis-ready-data/ga_ls5t_ard_3/088/080/1990/11/15
                    # /ga_ls5t_ard_3-0-0_088080_1990-11-15_final.odc-metadata.yaml

                    already_processed = check_granule_exists(
                        s3_bucket, s3_metadata_file
                    )

                    # Check if already processed and update flag set to force replace
                    if not already_processed or update:
                        try:
                            sync_granule(granule, nci_dir, s3_root_path, s3_bucket)
                            LOG.info(f"Finished S3 sync of granule - {granule}")

                            # s3 sync and metadata update happen in same section
                            metadata_update_error_list = update_metadata(
                                metadata_file,
                                s3_bucket,
                                s3_base_url,
                                explorer_base_url,
                                sns_topic,
                                s3_path,
                            )
                            error_list.extend(metadata_update_error_list)

                        # if the s3 sync has exception, not touch metadata
                        except S3SyncException as exp:
                            LOG.error(
                                f"Failed to sync of {granule} "
                                f"because of an error in the sync command - {exp}"
                            )
                            error_list.append(
                                f"Failed to sync of {granule} "
                                f"because of an error in the sync command - {exp}"
                            )

                    else:
                        LOG.warning(
                            f"Metadata exists in S3 and update is not set to True, "
                            f"not syncing {granule}"
                        )

                else:
                    LOG.error(
                        f"Failed to sync {metadata_file} "
                        f"because of missing metadata file in NCI"
                    )
                    error_list.append(
                        f"Failed to sync {metadata_file} "
                        f"because of missing metadata file in NCI"
                    )
    else:
        LOG.warning("Didn't find any granules to process...")

    # Raise exception if there was any error during sync process
    if error_list:
        raise S3SyncException("\n".join(error_list))


class S3SyncException(Exception):
    """
    Exception to raise for failure to sync with AWS S3
    """

    pass


@click.command()
@click.option("--filepath", "-f", type=str, required=True)
@click.option("--ncidir", "-n", type=str, required=True)
@click.option("--s3path", "-p", type=str, required=True)
@click.option("--s3bucket", "-b", type=str, required=True)
@click.option("--s3baseurl", "-u", type=str, default="")
@click.option("--explorerbaseurl", "-e", type=str, default="")
@click.option("--snstopic", "-t", type=str, required=True)
@click.option("--force-update", is_flag=True)
def main(
    filepath,
    ncidir,
    s3path,
    s3bucket,
    s3baseurl,
    explorerbaseurl,
    snstopic,
    force_update,
):
    """
    Script to sync Collection 3 data from NCI to AWS S3 bucket

    :param filepath: Path of the file containing list of scenes path extracted from Database
    :param ncidir: Source directory for the files in NCI
    :param s3path: Root folder of the S3 bucket
    :param s3bucket: Name of the S3 bucket
    :param s3baseurl: Base URL of the S3 bucket
    :param explorerbaseurl: Base URL of the Explorer
    :param snstopic: ARN of the SNS topic
    :param force_update: If this flag is set then do a fresh sync of data and
    replace the metadata
    """
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    LOG.setLevel(logging.DEBUG)
    LOG.addHandler(handler)
    LOG.info(
        f"Syncing granules listed in file {filepath} "
        f"from NCI dir {ncidir} "
        f"into the {s3bucket}/{s3path} and "
        f"S3 base URL is {s3baseurl} and "
        f"explorerbaseurl is {explorerbaseurl} and "
        f"snstopic is {snstopic} and "
        f"update is {force_update}"
    )
    sync_granules(
        filepath,
        ncidir,
        s3path,
        s3bucket,
        s3baseurl,
        explorerbaseurl,
        snstopic,
        force_update,
    )


if __name__ == "__main__":
    main()
