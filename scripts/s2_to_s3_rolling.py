#!/usr/bin/env python3
"""Sync data into AWS S3 bucket"""

import datetime
import logging
import os
import subprocess
import sys
import re

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
    """Find granules for the date range specified above. Format is yyyy-mm-dd/granule"""
    # Find the dates between the input date and today, inclusive, formatted like the directories
    dates = [(_end_date - datetime.timedelta(days=x)
              ).strftime("%Y-%m-%d") for x in range(_num_days + 1)]

    # The list of folders will be returned and will contain all the granules available for
    # the date range specified above. Format is yyyy-mm-dd/granule
    list_of_granules = []

    for date in dates:
        dir_for_date = os.path.join(root_path, date)
        if os.path.exists(dir_for_date):
            granules = [date + "/" + name for name in os.listdir(dir_for_date)]
            list_of_granules += granules

    return list_of_granules


def check_granule_exists(_s3_bucket, s3_metadata_path):
    """Check if granaule already exists in S3 bucket"""
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
    """Run AWS sync command to sync granules to S3 bucket"""
    local_path = os.path.join(NCI_DIR, granule)
    s3_path = "s3://{s3_bucket}/{s3_path}/{granule}".format(
        s3_bucket=_s3_bucket,
        s3_path=S3_PATH,
        granule=granule
    )

    # Remove any data that shouldn't be there and exclude the metadata and NBART
    command = "aws s3 sync {local_path} {s3_path} " \
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
    """Replace metadata with additional info"""
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


def sync_dates(_num_days, _s3_bucket, _end_date, _update='no'):
    """"Sync granules to S3 bucket for specified dates"""
    # Since all file paths are of the form:
    # /g/data/if87/datacube/002/S2_MSI_ARD/packaged/YYYY-mm-dd/<granule>
    # we can simply list all the granules per date and sync them
    if _end_date == 'today':
        datetime_end = datetime.datetime.today()
    else:
        datetime_end = datetime.datetime.strptime(_end_date, "%Y-%m-%d")

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
            if os.path.exists(yaml_file):
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
                if not already_processed and _update == 'no':
                    sync_action = 'sync_granule_metadata'
                else:
                    sync_action = _update

                if sync_action != 'no':
                    if sync_action in ('sync_granule_metadata', 'sync_granule'):
                        sync_success = sync_granule(granule, _s3_bucket)
                    else:
                        sync_success = True

                    if sync_success and (sync_action in ('sync_metadata', 'sync_granule_metadata')):
                        # Replace the metadata with a deterministic ID
                        replace_metadata(yaml_file, _s3_bucket, s3_metadata_path)
                        LOG.info("Finished processing and/or uploaded metadata to %s",
                                 s3_metadata_path)
                    else:
                        LOG.error("Failed to sync data... skipping")
                else:
                    LOG.warning("Metadata exists, not syncing %s", granule)
            else:
                LOG.error("Metadata is missing, not syncing %s", granule)
    else:
        LOG.warning("Didn't find any granules to process...")


def generate_log_report(file_path, _pbs_id):
    """Generate log report from existing log files"""
    log_files = ["{}/{}.ER".format(file_path, _pbs_id), "{}/{}.OU".format(file_path, _pbs_id)]
    export_file = "{}/log_report_{}.txt".format(file_path, _pbs_id)
    log_error_list = {
        "processing": {
            "keyword": "Processing",
            "desc": "Granules processed"
        },
        "failed": {
            "keyword": "Failed to sync data... skipping",
            "desc": "Failed to sync data... skipping"
        },
        "metadata_not_sync": {
            "keyword": "Metadata exists, not syncing",
            "desc": "Metadata exists but not syncing"
        },
        "no_metadata_not_sync": {
            "keyword": "Metadata is missing, not syncing",
            "desc": "Metadata is missing so not syncing"
        },
        "finished_processing_granule": {
            "keyword": "Finished processing of granule - ",
            "desc": "Finished processing of granule"
        },
        "failed_processing_granule": {
            "keyword": "Failed processing of granule",
            "desc": "Failed processing of granule"
        },
        "finished_metadata_upload": {
            "keyword": "Finished uploaded metadata",
            "desc": "Finished uploaded metadata"
        },
        "finished_processing_metadata_upload": {
            "keyword": "Finished processing and/or uploaded metadata to",
            "desc": "Finished processing and/or uploaded metadata"
        }
    }

    match_list_all = parse_log_data(log_files, log_error_list, read_line=True)
    write_log_report(export_file, log_error_list, match_list_all)


def parse_log_data(log_files, log_error_list, read_line=True):
    """Parse logged data to generate report"""
    match_list_all = {}
    for log_file in log_files:
        with open(log_file, "r") as file:
            if read_line:
                for line in file:
                    for name, regex in log_error_list.items():
                        for match in re.finditer(regex["keyword"], line, re.S):
                            match_list_all.setdefault(name, []).append(line)
            else:
                data = file.read()
                for name, regex in log_error_list.items():
                    match_list = []
                    for match in re.finditer(regex["keyword"], data, re.S):
                        match_text = match.group()
                        match_list.append(match_text)
                    match_list_all[name] = match_list
        file.close()
    return match_list_all


def write_log_report(export_file, log_error_list, match_list_all):
    """Writes log report into file"""
    with open(export_file, "w+") as file:
        file.write("LOG REPORT SUMMARY:\n")
        for name, value in match_list_all.items():
            txt = "{} - COUNT: {}".format(log_error_list[name]['desc'], len(value))
            file.write(txt + "\n")
        file.write("\nLOG REPORT DETAILS:")
        for name, value in match_list_all.items():
            file.write("\n::: " + log_error_list[name]['desc'] + " :::\n")
            for text in value:
                file.write(text)
    file.close()


if __name__ == '__main__':
    # Arg 1 is action
    action = sys.argv[1]
    if action == "log":
        # Arg 2 is path, 3 is pbs_id
        path = sys.argv[2]
        pbs_id = sys.argv[3]
        LOG.info("Analysing log in path %s with PBS ID (%s)", path, pbs_id)
        generate_log_report(path, pbs_id)
    else:
        # Arg 2 is numdays, 3 is bucket, 4 is enddate, 5 is do_update
        num_days = int(sys.argv[2])
        s3_bucket = sys.argv[3]
        end_date = sys.argv[4]
        try:
            DO_UPDATE = sys.argv[5]
        except IndexError:
            DO_UPDATE = 'no'
        LOG.info("Syncing %s days back from %s into the %s bucket and update is %s",
                 num_days, end_date, s3_bucket, DO_UPDATE)
        sync_dates(num_days, s3_bucket, end_date, DO_UPDATE)
