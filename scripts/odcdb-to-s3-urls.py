#!/usr/bin/env python

from datetime import date

from datacube import Datacube

dc = Datacube()


# s3://dea-public-data/L2/sentinel-2-nbar/S2MSIARD_NBAR/2020-10-19/S2B_OPER_MSI_ARD_TL_VGS1_20201019T060322_A018905_T50LNP_N02.09/ARD-METADATA.yaml
#
#  's2a_ard_granule',
#  's2b_ard_granule',
#

def ds_to_s3_url(ds):
    # return f"s3://dea-public-data/L2/sentinel-2-nbar/S2MSIARD_NBAR/{ds.key_time.strftime('%Y-%m-%d')}/{ds.metadata_doc['tile_id'].replace('L1C', 'ARD')}/ARD-METADATA.yaml"
    # Don't trust the datetimes that are exposed!
    return f"s3://dea-public-data/L2/sentinel-2-nbar/S2MSIARD_NBAR/{ds.metadata_doc['extent']['center_dt'][:10]}/{ds.metadata_doc['tile_id'].replace('L1C', 'ARD')}/ARD-METADATA.yaml"


for product in ('s2a_ard_granule', 's2b_ard_granule'):
    for year in range(2017, date.today().year + 1):
        for month in range(1, 13):

            for ds in dc.find_datasets(product=product, time=f'{year}-{month:02}'):
                print(ds_to_s3_url(ds))
