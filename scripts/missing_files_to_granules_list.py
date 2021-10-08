#!/usr/bin/env python3
"""
Script to convert S3 inventory to granules list CSV. This CSV can be use in c3_to_s3_rolling:execute_c3_to_s3_script step.

These txt files come from:

s3-inventory-dump --prefix baseline | tqdm > baseline-inventory.txt


Input example:

['./find-missing-tiffs.py']
loading inventory
inventory loaded
26: s3://dea-public-data/baseline/ga_ls7e_ard_3/088/080/1999/08/12/ga_ls7e_ard_3-0-0_088080_1999-08-12_final.odc-metadata.yaml
   ga_ls7e_ard_3-0-0_088080_1999-08-12_final.odc-metadata.yaml
   ga_ls7e_ard_3-0-0_088080_1999-08-12_final.proc-info.yaml
   ga_ls7e_ard_3-0-0_088080_1999-08-12_final.sha1
   ga_ls7e_ard_3-0-0_088080_1999-08-12_final.stac-item.json
   ga_ls7e_nbart_3-0-0_088080_1999-08-12_final_band01.tif
   ga_ls7e_nbart_3-0-0_088080_1999-08-12_final_band02.tif
   ga_ls7e_nbart_3-0-0_088080_1999-08-12_final_band03.tif
   ga_ls7e_nbart_3-0-0_088080_1999-08-12_final_band04.tif
   ga_ls7e_nbart_3-0-0_088080_1999-08-12_final_band05.tif
   ga_ls7e_nbart_3-0-0_088080_1999-08-12_final_band07.tif
   ga_ls7e_nbart_3-0-0_088080_1999-08-12_final_band08.tif
   ga_ls7e_nbart_3-0-0_088080_1999-08-12_final_thumbnail.jpg
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_azimuthal-exiting.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_azimuthal-incident.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_combined-terrain-shadow.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_exiting-angle.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_fmask.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_incident-angle.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_nbart-contiguity.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_relative-azimuth.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_relative-slope.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_satellite-azimuth.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_satellite-view.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_solar-azimuth.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_solar-zenith.tif
   ga_ls7e_oa_3-0-0_088080_1999-08-12_final_time-delta.tif
25: s3://dea-public-data/baseline/ga_ls7e_ard_3/093/075/2021

Output example:

///g/data/xu18/ga/ga_ls7e_ard_3/088/080/1999/08/12/ga_ls7e_ard_3-0-0_088080_1999-08-12_final.odc-metadata.yaml,,

Note: the two , in the CSV are not typo. There are 3 columns in CSV. Only the first column is useful (metadata NCI path).

"""

import csv

file_path_list = ["ls7.txt", "ls8.txt"]

metadata_list = []

for file_path in file_path_list:
    with open(file_path, 'r') as file:
        # only grab the metadata file
        [metadata_list.append(e.replace('\n', '')) for e in file.readlines() if 's3://dea-public-data' in e]

# the metadata right now is: '26: s3://dea-public-data/baseline/ga_ls7e_ard_3/088/080/1999/08/12/ga_ls7e_ard_3-0-0_088080_1999-08-12_final.odc-metadata.yaml'
# let's convert it to NCI format
metadata_list = [e.split(': ')[-1].replace('s3://dea-public-data/baseline/', '///g/data/xu18/ga/') for e in metadata_list]

# now, convert it to the CSV format
with open('incorrect_metadata_in_s3.csv', 'w', newline='') as csv_file:
    writer = csv.writer(csv_file)
    for metadata in metadata_list:            
        writer.writerow([metadata, "", ""])