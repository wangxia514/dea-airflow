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


s3_bucket = 'dea-public-data-dev'


def data_verification(data_check_path, missing_file_path):
    """
    Check if files from data_check.txt have been successfully uploaded to s3
    :param data_check_path: path for the data_check.txt. contains listing of files to check
    :param missing_file_path: path for the missing_file.txt. contains listing of missing files
    :return: list of missing files
    """
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

    missing_files = []

    with open(data_check_path, "r") as data_check_file, open(missing_file_path, "a") as missing_file:
        data_check_reader = csv.reader(data_check_file, delimiter=',')
        for row in data_check_reader:
            try:
                key_path = os.path.relpath(row[0], f"s3://{s3_bucket}")
                s3.head_object(Bucket=s3_bucket, Key=key_path)
            except ClientError as error:
                print(f"Error {error}. {key_path} not found in {s3_bucket}")
                missing_file.write(f"{row[0]}\n")
                missing_files.append(row[0])
                pass

    missing_file_count = len(missing_files)
    print(f"Missing file count {missing_file_count}.")

    return missing_files


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
