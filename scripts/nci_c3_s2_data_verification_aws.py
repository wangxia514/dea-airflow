"""
Script to perform data verification checks
"""

import csv
import argparse
import boto3
import os
from botocore.errorfactory import ClientError
from botocore import UNSIGNED
from botocore.config import Config


s3_bucket = 'dea-public-data'
product_path = 'baseline'
nci_directory = '/g/data/ka08/ga'


def data_verification(data_check_path, missing_file_path):
    """
    Check if files from data_check.txt have been successfully uploaded to s3
    :param data_check_path: path for the data_check.txt. contains listing of files to check
    :param missing_file_path: path for the missing_file.txt. contains listing of missing files
    """
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

    missing_files = []

    # testing for individual files within each granule to see if its there
    with open(data_check_path, "r") as data_check_file:
        data_check_reader = csv.reader(data_check_file, delimiter=',')
        for row in data_check_reader:
            key_path = os.path.relpath(row[0], f"s3://{s3_bucket}")
            try:
                s3.head_object(Bucket=s3_bucket, Key=key_path)
            except ClientError as error:
                print(f"Error {error}. {key_path} not found in {s3_bucket}")

                # add granule which has file missing to list
                s2_path = os.path.dirname(row[0])
                missing_files.append(s2_path)
                pass

    missing_file_count = len(missing_files)
    print(f"Missing file count {missing_file_count}.")

    # remove any duplicate folder entries as more than one file for a granule could be missing
    missing_folders_cleaned = set(missing_files)

    # add missing granule folder to list for retry even if just one file missing from granule to ensure completeness
    with open(missing_file_path, "w") as missing_file:
        for row in missing_folders_cleaned:
            key_path = os.path.relpath(row, f"s3://{s3_bucket}")
            nci_path = os.path.relpath(key_path, product_path)
            missing_file.write(f"cp -acl bucket-owner-full-control {nci_directory}/{nci_path}/* {row}/\n")


if __name__ == '__main__':
    # Arguments Setup
    main_parser = argparse.ArgumentParser(
        description='Generate s5cmd commands')
    main_parser.add_argument('--data_check_path', required=True,
                             help='Location of the data check file')
    main_parser.add_argument('--missing_file_path', required=True,
                             help='Location of the missing file path')

    args = main_parser.parse_args()
    data_check_path = args.data_check_path
    missing_file_path = args.missing_file_path

    data_verification(data_check_path, missing_file_path)
