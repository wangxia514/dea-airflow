"""
Script to convert granule_id.txt to s5cmd commands and create a text file for post sync data verification checks
"""

import csv
import argparse
import json
import os


s3_bucket = 's3://dea-public-data'
product_path = 'baseline'
nci_directory = '/g/data/ka08/ga'


def gen_s5cmd_commands(granule_id_location, output_path, data_check_path):
    """
    Convert granules.txt into s5cmd commands file and creates a text file for post sync data verification checks.
    :param granule_id_location: location of granule_id.txt file generated by ODC queries
    :param output_path: location of the output commands.txt file. This used by s5cmd for data syncing
    :param data_check_path: location of the output data_check.txt file. This is used for data verification checks
    post data syncing
    """
    with open(granule_id_location, "r") as granule_id_file, open(output_path, mode='w') as s5cmd_file, open(
            data_check_path, mode='w') as data_check_file:
        granule_id_reader = csv.reader(granule_id_file, delimiter=',')

        for row in granule_id_reader:
            metadata_path = row[0]
            archived_date = row[1]
            added_date = row[2]
            metadata = row[3]

            metadata_json = json.loads(metadata)
            measurements = metadata_json["measurements"]

            granule_file_listing = []

            # create list of items in granule from metadata
            for item in measurements:
                granule_file_listing.append(measurements[item]["path"])

            # parse nci listing for folder locations
            nci_path = os.path.dirname(metadata_path)
            nci_path_prefix = os.path.relpath(nci_path, nci_directory)
            s3_path = f"{s3_bucket}/{product_path}/{nci_path_prefix}"

            # generate copy commands if not archived otherwise remove data
            if archived_date is None or archived_date == '':
                s5cmd_file.write(f"cp -acl bucket-owner-full-control {nci_path}/* {s3_path}/\n")

                # create list of files to check after syncing complete
                for item in granule_file_listing:
                    data_check_file.write(f"{s3_path}/{item}\n")

                nci_metadata_path_prefix = os.path.relpath(metadata_path, nci_directory)
                data_check_file.write(f"{s3_bucket}/{product_path}/{nci_metadata_path_prefix}\n")
                stac_metadata_path = nci_metadata_path_prefix.replace("odc-metadata.yaml", "stac-item.json")
                data_check_file.write(f"{s3_bucket}/{product_path}/{stac_metadata_path}\n")

            else:
                # need to update indexing to be able to archive from s3 event first before enabling below
                """
                s5cmd_file.write(f"rm {nci_path}/* {s3_path}/\n")
                """


if __name__ == '__main__':
    # Arguments Setup
    main_parser = argparse.ArgumentParser(
        description='Generate s5cmd commands')
    main_parser.add_argument('--granule_id', required=True,
                             help='Location of the granule_id.txt')
    main_parser.add_argument('--commands_path', required=True,
                             help='Location of the s5cmd commands file')
    main_parser.add_argument('--data_check_path', required=True,
                             help='Location of the data check file')
    main_parser.add_argument('--overwrite', action='store_const',
                             const=True, required=False, default=False,
                             help='Boolean whether to overwrite output file')

    args = main_parser.parse_args()
    granule_id_location = args.granule_id
    output_path = args.commands_path
    data_check_path = args.data_check_path
    overwrite = args.overwrite

    gen_s5cmd_commands(granule_id_location, output_path, data_check_path)
