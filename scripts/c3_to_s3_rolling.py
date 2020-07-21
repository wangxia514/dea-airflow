#!/usr/bin/env python3
"""
Script to sync Collection 3 data from NCI to AWS S3 bucket
"""
import io
import json
import logging
import math
import subprocess
from datetime import datetime
from pathlib import Path

from botocore.exceptions import ClientError
import boto3
import click
from ruamel.yaml import YAML

from eodatasets3 import verify, serialise
from eodatasets3.scripts import tostac
from datacube.utils.geometry import Geometry, CRS
from odc.index import odc_uuid


formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
LOG = logging.getLogger("c3_to_s3_rolling")
LOG.setLevel(logging.DEBUG)
LOG.addHandler(handler)


# STAC content for Landsat collection 3 data
# Todo: Create a separate json file
ga_ls_ard_3_stac_item = {
  "stac_version": "1.0.0-beta.1",
  "stac_extensions": [
    "eo"
  ],
  "type": "Feature",
  "assets": {
    "nbar_nir": {
      "eo:bands": [
        {
          "name": "nbar_nir"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbar_red": {
      "eo:bands": [
        {
          "name": "nbar_red"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_fmask": {
      "eo:bands": [
        {
          "name": "oa_fmask"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbar_blue": {
      "eo:bands": [
        {
          "name": "nbar_blue"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbart_nir": {
      "eo:bands": [
        {
          "name": "nbart_nir"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbart_red": {
      "eo:bands": [
        {
          "name": "nbart_red"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbar_green": {
      "eo:bands": [
        {
          "name": "nbar_green"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbart_blue": {
      "eo:bands": [
        {
          "name": "nbart_blue"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbar_swir_1": {
      "eo:bands": [
        {
          "name": "nbar_swir_1"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbar_swir_2": {
      "eo:bands": [
        {
          "name": "nbar_swir_2"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbart_green": {
      "eo:bands": [
        {
          "name": "nbart_green"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbart_swir_1": {
      "eo:bands": [
        {
          "name": "nbart_swir_1"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbart_swir_2": {
      "eo:bands": [
        {
          "name": "nbart_swir_2"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_time_delta": {
      "eo:bands": [
        {
          "name": "oa_time_delta"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_solar_zenith": {
      "eo:bands": [
        {
          "name": "oa_solar_zenith"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_exiting_angle": {
      "eo:bands": [
        {
          "name": "oa_exiting_angle"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_solar_azimuth": {
      "eo:bands": [
        {
          "name": "oa_solar_azimuth"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_incident_angle": {
      "eo:bands": [
        {
          "name": "oa_incident_angle"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_relative_slope": {
      "eo:bands": [
        {
          "name": "oa_relative_slope"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_satellite_view": {
      "eo:bands": [
        {
          "name": "oa_satellite_view"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_nbar_contiguity": {
      "eo:bands": [
        {
          "name": "oa_nbar_contiguity"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_nbart_contiguity": {
      "eo:bands": [
        {
          "name": "oa_nbart_contiguity"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_relative_azimuth": {
      "eo:bands": [
        {
          "name": "oa_relative_azimuth"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_azimuthal_exiting": {
      "eo:bands": [
        {
          "name": "oa_azimuthal_exiting"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_satellite_azimuth": {
      "eo:bands": [
        {
          "name": "oa_satellite_azimuth"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_azimuthal_incident": {
      "eo:bands": [
        {
          "name": "oa_azimuthal_incident"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "oa_combined_terrain_shadow": {
      "eo:bands": [
        {
          "name": "oa_combined_terrain_shadow"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbar_panchromatic": {
      "eo:bands": [
        {
          "name": "nbar_panchromatic"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbar_coastal_aerosol": {
      "eo:bands": [
        {
          "name": "nbar_coastal_aerosol"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbart_panchromatic": {
      "eo:bands": [
        {
          "name": "nbart_panchromatic"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "nbart_coastal_aerosol": {
      "eo:bands": [
        {
          "name": "nbart_coastal_aerosol"
        }
      ],
      "type": "image/tiff; application=geotiff",
      "roles": [
        "data"
      ]
    },
    "thumbnail:nbar": {
      "title": "Thumbnail image",
      "type": "image/jpeg",
      "roles": [
        "thumbnail"
      ]
    },
    "thumbnail:nbart": {
      "title": "Thumbnail image",
      "type": "image/jpeg",
      "roles": [
        "thumbnail"
      ]
    },
    "checksum:sha1": {
      "type": "text/plain"
    },
    "metadata:processor": {
      "type": "text/plain",
      "roles": [
        "metadata"
      ]
    }
  }
}


# Todo: Update/Use eodatasets3 to STAC v1.0.0-beta.1
def create_stac(dataset, input_metadata, output_path, stac_data, base_url):
    """
    Create STAC metadata

    :param dataset: Dict of the metadata content
    :param input_metadata: Path of the Input metadata file
    :param output_path: Path of the STAC output file
    :param stac_data: Dict of the static STAC content
    :param base_url: Base URL path for STAC file
    :return: Dict of the STAC content
    """

    wgs84_geometry = Geometry(dataset["geometry"], CRS(dataset["crs"])).to_crs(CRS("epsg:4326"), math.inf)
    item_doc = dict(
        stac_version=stac_data["stac_version"] if "stac_version" in stac_data else "1.0.0-beta.1",
        stac_extensions=stac_data["stac_extensions"] if "stac_extensions" in stac_data else [],
        id=dataset["id"],
        type=stac_data["type"] if "type" in stac_data else "Feature",
        bbox=wgs84_geometry.boundingbox,
        geometry=wgs84_geometry.json,
        properties={**dataset["properties"], "odc:product": dataset["product"]["name"]},
        assets={
            **{name: (
                {**stac_data["assets"][name], "href": base_url + m["path"]}
                if "assets" in stac_data and name in stac_data["assets"] else
                {"href": base_url + m["path"]}
            ) for name, m in dataset["measurements"].items()},
            **{name: (
                {**stac_data["assets"][name], "href": base_url + m["path"]}
                if "assets" in stac_data and name in stac_data["assets"] else
                {"href": base_url + m["path"]}
            ) for name, m in dataset["accessories"].items()},
        },
        links=[
            {
                "rel": "self",
                "type": "application/json",
                "href": base_url + output_path.name
            },
            {
                "title": "STAC's Source Item",
                "rel": "derived_from",
                "href": base_url + input_metadata.name
            },
            {
                "rel": "odc_product",
                "type": "text/html",
                "href": dataset["product"]["href"]
            },
            {
                "rel": "alternative",
                "type": "text/html",
                "href": f"https://explorer.dea.ga.gov.au/dataset/{dataset['id']}",
            },
        ],
    )
    return item_doc


def find_granules(file_path):
    """
    Load a list of metadata files in NCI

    :param file_path: File with metadata list
    :return: List of granules
    """
    with open(file_path, 'r') as f:
        return [x.strip() for x in f.readlines()]


def check_granule_exists(_s3_bucket, s3_metadata_path):
    """
    Check if granaule already exists in S3 bucket

    :param _s3_bucket: Name of s3 bucket to store granules
    :param s3_metadata_path: Path of metadata file
    :return: True if success else False
    """
    s3_resource = boto3.resource('s3')

    try:
        # This does a head request, so is fast
        s3_resource.Object(_s3_bucket, s3_metadata_path).load()
    except ClientError as exception:
        if exception.response['Error']['Code'] == "404":
            return False
    else:
        return True


def upload_s3_resource(s3_bucket, s3_file, obj):
    """
    Upload s3 resource object in provided s3 path

    :param s3_bucket: Name of s3 bucket to store granules
    :param s3_file: Path of metadata file
    :param obj: Resource object to upload
    """
    try:
        s3_resource = boto3.resource("s3").Bucket(s3_bucket)
        s3_resource.Object(key=s3_file).put(Body=obj)
    except ValueError as exception:
        raise S3SyncException(str(exception))
    except ClientError as exception:
        raise S3SyncException(str(exception))


def publish_sns(sns_topic, message, message_attributes):
    """
    Publish message containing STAC metadata to SNS Topic

    :param sns_topic: ARN of the SNS Topic
    :param message: SNS message
    :param message_attributes: SNS message attributes
    """
    try:
        sns_client = boto3.client('sns')
        sns_client.publish(TopicArn=sns_topic,
                           Message=message,
                           MessageAttributes=message_attributes
                           )
    except ClientError as exception:
        raise S3SyncException(str(exception))


def upload_checksum(nci_metadata_file_path, checksum_file_path, new_checksum_list, s3_bucket, s3_path):
    """
    Updates and uploads checksum file

    :param nci_metadata_file_path: Path of metadata file
    :param checksum_file_path: Path of checksum file
    :param new_checksum_list: List of filename and updated checksum
    :param s3_bucket: Name of the S3 bucket
    :param s3_path: Path of the S3 bucket
    """

    # Identify list of files to be included in checksum file
    excluded_files = []
    excluded_pattern = ["ga_*_nbar_*.*",
                        "ga_*_nbar-*.*",
                        nci_metadata_file_path.name,
                        checksum_file_path.name]
    for ex_pat in excluded_pattern:
        for path in checksum_file_path.parent.glob(ex_pat):
            excluded_files.append(path.name)

    # Read checksum for files to be included
    with checksum_file_path.open('r') as f:
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
        upload_s3_resource(s3_bucket, s3_checksum_file, temp_checksum.getvalue())


def update_metadata(nci_metadata_file, s3_bucket, s3_base_url, sns_topic, s3_path):
    """
    Uploads updated metadata with nbar element removed, updated checksum file, STAC doc created
    and publish SNS message

    :param nci_metadata_file: Path of metadata file in NCI
    :param s3_bucket: Name of S3 bucket
    :param s3_base_url: Base URL of the S3 bucket
    :param sns_topic: ARN of the SNS topic
    :param s3_path: Path in S3
    :return: List of errors
    """
    # Initialise error list
    metadata_error_list = []
    # Initialise checksum list
    new_checksum_list = {}

    # Initialise YAML
    yaml = YAML()
    yaml.representer.add_representer(datetime, serialise.represent_datetime)
    yaml.width = 80
    yaml.explicit_start = True
    yaml.explicit_end = True

    nci_metadata_file_path = Path(nci_metadata_file)
    with nci_metadata_file_path.open("r") as f:
        temp_metadata = yaml.load(f)

    # Add original UUID to new field 'original_id'
    temp_metadata['original_id'] = temp_metadata['id']

    # Create a new deterministic dataset ID
    temp_metadata['id'] = str(odc_uuid("c3_to_s3_rolling", "1.0.0", [temp_metadata['id']]))

    # Deleting Nbar related metadata
    # Because Landsat 8 is different, we need to check if the fields exist
    # before removing them.
    if "nbar_blue" in temp_metadata['measurements']:
        del temp_metadata['measurements']['nbar_blue']
    if "nbar_green" in temp_metadata['measurements']:
        del temp_metadata['measurements']['nbar_green']
    if "nbar_nir" in temp_metadata['measurements']:
        del temp_metadata['measurements']['nbar_nir']
    if "nbar_red" in temp_metadata['measurements']:
        del temp_metadata['measurements']['nbar_red']
    if "nbar_swir_1" in temp_metadata['measurements']:
        del temp_metadata['measurements']['nbar_swir_1']
    if "nbar_swir_2" in temp_metadata['measurements']:
        del temp_metadata['measurements']['nbar_swir_2']
    if "nbar_coastal_aerosol" in temp_metadata['measurements']:
        del temp_metadata['measurements']['nbar_coastal_aerosol']
    if "nbar_panchromatic" in temp_metadata['measurements']:
        del temp_metadata['measurements']['nbar_panchromatic']
    if "oa_nbar_contiguity" in temp_metadata['measurements']:
        del temp_metadata['measurements']['oa_nbar_contiguity']
    if "thumbnail:nbar" in temp_metadata['accessories']:
        del temp_metadata['accessories']['thumbnail:nbar']

    # Dump metadata yaml into buffer
    with io.BytesIO() as temp_yaml:
        yaml.dump(temp_metadata, temp_yaml)
        temp_yaml.seek(0)  # Seek back to the beginning of the file before next read/write
        new_checksum_list[nci_metadata_file_path.name] = verify.calculate_hash(temp_yaml)

        # Write odc metadata yaml object into S3
        s3_metadata_file = f"{s3_path}/{nci_metadata_file_path.name}"
        try:
            upload_s3_resource(s3_bucket, s3_metadata_file, temp_yaml.getvalue())
            LOG.info(f"Finished uploading metadata to {s3_metadata_file}")
        except S3SyncException as exp:
            LOG.error(f"Failed uploading metadata to {s3_metadata_file} - {exp}")
            metadata_error_list.append(f"Failed uploading metadata to {s3_metadata_file} - {exp}")

    # Create stac metadata
    name = nci_metadata_file_path.stem.replace(".odc-metadata", "")
    stac_output_file_path = nci_metadata_file_path.with_name(f"{name}.stac-item.json")
    stac_data = ga_ls_ard_3_stac_item if ga_ls_ard_3_stac_item else {}
    stac_url_path = f"{s3_base_url}/{s3_path}/" if s3_base_url else ""
    item_doc = create_stac(temp_metadata,
                           nci_metadata_file_path,
                           stac_output_file_path,
                           stac_data,
                           stac_url_path
                           )
    stac_dump = json.dumps(item_doc, indent=4, default=tostac.json_fallback)

    # Write stac json to buffer
    with io.BytesIO() as temp_stac:
        temp_stac.write(stac_dump.encode())
        temp_stac.seek(0)  # Seek back to the beginning of the file before next read/write
        new_checksum_list[stac_output_file_path.name] = verify.calculate_hash(temp_stac)

        # Write stac metadata json object into S3
        s3_stac_file = f"{s3_path}/{stac_output_file_path.name}"
        try:
            upload_s3_resource(s3_bucket, s3_stac_file, temp_stac.getvalue())
            LOG.info(f"Finished uploading STAC metadata to {s3_stac_file}")
        except S3SyncException as exp:
            LOG.error(f"Failed uploading STAC metadata to {s3_stac_file} - {exp}")
            metadata_error_list.append(f"Failed uploading STAC metadata to {s3_stac_file} - {exp}")

    # Publish message containing STAC metadata to SNS Topic
    message_attributes = {
        "collection": {
            "DataType": "String",
            "StringValue": item_doc["properties"]["odc:product"]
        }
    }
    try:
        publish_sns(sns_topic, stac_dump, message_attributes)
        LOG.info(f"Finished publishing SNS Message to SNS Topic {sns_topic}")
    except S3SyncException as exp:
        LOG.error(f"Failed publishing SNS Message to SNS Topic {sns_topic} - {exp}")
        metadata_error_list.append(f"Failed publishing SNS Message to SNS Topic {sns_topic} - {exp}")

    # Update checksum file
    checksum_filename = nci_metadata_file_path.stem.replace(".odc-metadata", "")
    checksum_file_path = nci_metadata_file_path.with_name(f"{checksum_filename}.sha1")
    try:
        upload_checksum(nci_metadata_file_path,
                        checksum_file_path,
                        new_checksum_list,
                        s3_bucket, s3_path)
        LOG.info(f"Finished uploading checksum file "
                 f"{s3_path}/{checksum_file_path.name}")
    except S3SyncException as exp:
        LOG.error(f"Failed uploading checksum file "
                  f"{s3_path}/{checksum_file_path.name} - {exp}")
        metadata_error_list.append(f"Failed uploading checksum file "
                                   f"{s3_path}/{checksum_file_path.name} - {exp}")

    return metadata_error_list


def sync_granule(granule, nci_dir, s3_root_path, s3_bucket):
    """
    Run AWS sync command to sync granules to S3 bucket

    :param granule: Name of the granule
    :param nci_dir: Source directory for the files in NCI
    :param s3_root_path: Root folder of the S3 bucket
    :param s3_bucket: Name of the S3 bucket
    :return: Returns code zero, if success.
    """
    local_path = Path(nci_dir).joinpath(granule)
    s3_path = f"s3://{s3_bucket}/{s3_root_path}/{granule}"

    # Remove any data that shouldn't be there and exclude the metadata
    command = f"aws s3 sync {local_path} {s3_path} " \
              "--no-progress " \
              "--delete " \
              "--exclude ga_*_nbar_*.* " \
              "--exclude ga_*_nbar-*.* " \
              "--exclude *.sha1 " \
              "--exclude ga_*.odc-metadata.yaml"

    return_code = subprocess.call(command, shell=True)

    if return_code != 0:
        raise S3SyncException(f"Failed running S3 sync command")


def sync_granules(file_path, nci_dir, s3_root_path, s3_bucket, s3_base_url, sns_topic, update=False):
    """
    Sync granules to S3 bucket for specified dates

    :param file_path: File path for the csv file listing scenes path
    :param nci_dir: Source directory for the files in NCI
    :param s3_root_path: Root folder of the S3 bucket
    :param s3_bucket: Name of the S3 bucket
    :param s3_base_url: Base URL of the S3 bucket
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
        for metadata_file in list_of_granules:
            LOG.info(f"Processing {metadata_file}")

            metadata_file_path = Path(metadata_file)

            # Checking if metadata file exists
            if metadata_file_path.exists():
                # s3://dea-public-data
                # /analysis-ready-data/ga_ls5t_ard_3/088/080/1990/11/15
                # /ga_ls5t_ard_3-0-0_088080_1990-11-15_final.odc-metadata.yaml

                granule = metadata_file_path.relative_to(nci_dir).parent
                metadata_file_name = metadata_file_path.name
                s3_path = f"{s3_root_path}/{granule}"
                s3_metadata_file = f"{s3_path}/{metadata_file_name}"

                already_processed = check_granule_exists(s3_bucket, s3_metadata_file)

                # Check if already processed and update flag set to force replace
                if not already_processed or update:
                    try:
                        sync_granule(granule, nci_dir, s3_root_path, s3_bucket)
                        LOG.info(f"Finished S3 sync of granule - {granule}")
                    except S3SyncException as exp:
                        LOG.error(f"Failed to sync of {granule} "
                                  f"because of an error in the sync command - {exp}")
                        error_list.append(f"Failed to sync of {granule} "
                                          f"because of an error in the sync command - {exp}"
                                          )

                    metadata_update_error_list = update_metadata(metadata_file,
                                                                 s3_bucket,
                                                                 s3_base_url,
                                                                 sns_topic,
                                                                 s3_path)
                    error_list.extend(metadata_update_error_list)

                else:
                    LOG.warning(f"Metadata exists in S3 and update is not set to True, "
                                f"not syncing {granule}")

            else:
                LOG.error(f"Failed to sync {metadata_file} "
                          f"because of missing metadata file in NCI")
                error_list.append(f"Failed to sync {metadata_file} "
                                  f"because of missing metadata file in NCI")
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
@click.option("--filepath", '-f', type=str, required=True)
@click.option("--ncidir", '-n', type=str, required=True)
@click.option("--s3path", '-p', type=str, required=True)
@click.option("--s3bucket", '-b', type=str, required=True)
@click.option("--s3baseurl", '-u', type=str, default="", required=True)
@click.option("--snstopic", '-t', type=str, required=True)
@click.option('--force-update', is_flag=True)
def main(filepath, ncidir, s3path, s3bucket, s3baseurl, snstopic, force_update):
    """
    Script to sync Collection 3 data from NCI to AWS S3 bucket

    :param filepath: Path of the file containing list of scenes path extracted from Database
    :param ncidir: Source directory for the files in NCI
    :param s3path: Root folder of the S3 bucket
    :param s3bucket: Name of the S3 bucket
    :param s3baseurl: Base URl of the S3 bucket
    :param snstopic: ARN of the SNS topic
    :param force_update: If this flag is set then do a fresh sync of data and
    replace the metadata
    """
    LOG.info(f"Syncing granules listed in file {filepath} "
             f"from NCI dir {ncidir} "
             f"into the {s3bucket}/{s3path} and "
             f"S3 base URL is {s3baseurl} and "
             f"snstopic is {snstopic} and "
             f"update is {force_update}")
    sync_granules(filepath, ncidir, s3path, s3bucket, s3baseurl, snstopic, force_update)


if __name__ == '__main__':
    main()
