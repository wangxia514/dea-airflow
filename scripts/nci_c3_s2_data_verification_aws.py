"""
Script to perform data verification checks
"""

import csv
import argparse
import boto3
from botocore.errorfactory import ClientError


s3_bucket = 'dea-public-data-dev'


def data_verification(data_check_path):
    """
    Check if files from data_check.txt have been successfully uploaded to s3
    :param data_check_path: path for the data_check.txt. contains listing of files to check
    :return: list of missing files
    """
    s3 = boto3.client('s3')

    missing_files = []

    with open(data_check_path, "r") as data_check_file:
        data_check_reader = csv.reader(data_check_file, delimiter=',')
        for row in data_check_reader:
            try:
                s3.head_object(Bucket=s3_bucket, Key=row[0])
            except ClientError:
                print('{} not found in {}'.format(row, s3_bucket))
                missing_files.append(row[0])
                pass

    return missing_files


if __name__ == '__main__':
    # Arguments Setup
    main_parser = argparse.ArgumentParser(
        description='Generate s5cmd commands')
    main_parser.add_argument('--data_check_path', required=True,
                             help='Location of the data check file')

    args = main_parser.parse_args()
    data_check_path = args.data_check_path

    data_verification(data_check_path)
