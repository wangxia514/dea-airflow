#!/bin/bash

### Add metadata ###
datacube metadata add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/nrt/sentinel/eo_s2_nrt.odc-type.yaml # for s2_nrt
datacube metadata add https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/eo3_landsat_ard.odc-type.yaml # for provisional ard

### add products and limited datasets ###
# s2 nrtproducts
datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/nrt/sentinel/s2_nrt.products.yaml # s2a_nrt_granule and s2b_nrt_granule

# s2a nrt granule datasets
datacube dataset add https://data.dea.ga.gov.au/L2/sentinel-2-nrt/S2MSIARD/2021-06-29/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00/ARD-METADATA.yaml --confirm-ignore-lineage
datacube dataset add https://data.dea.ga.gov.au/L2/sentinel-2-nrt/S2MSIARD/2021-08-28/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01/ARD-METADATA.yaml --confirm-ignore-lineage
datacube dataset add https://data.dea.ga.gov.au/L2/sentinel-2-nrt/S2MSIARD/2021-08-28/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01/ARD-METADATA.yaml --confirm-ignore-lineage
datacube dataset add https://data.dea.ga.gov.au/L2/sentinel-2-nrt/S2MSIARD/2021-08-29/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01/ARD-METADATA.yaml --confirm-ignore-lineage

# s2b nrt granule datasets (used in delete dataset location dag)
datacube dataset add https://data.dea.ga.gov.au/L2/sentinel-2-nrt/S2MSIARD/2021-09-06/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01/ARD-METADATA.yaml --confirm-ignore-lineage
datacube dataset update s3://dea-public-data/L2/sentinel-2-nrt/S2MSIARD/2021-09-06/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01/ARD-METADATA.yaml

# provisional products
datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls7_provisional.odc-product.yaml # ls7 provision products
datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls8_provisional.odc-product.yaml # ls8 provisional products
datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2a_provisional.odc-product.yaml # s2a provisional products
datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2b_provisional.odc-product.yaml # s2b provisional products

# ga_ls7/ls8 provisional datasets
datacube dataset add https://data.dea.ga.gov.au/baseline/ga_ls7e_ard_provisional_3/103/076/2021/08/18_nrt/ga_ls7e_ard_provisional_3-2-1_103076_2021-08-18_nrt.odc-metadata.yaml --confirm-ignore-lineage
datacube dataset add https://data.dea.ga.gov.au/baseline/ga_ls7e_ard_provisional_3/103/076/2021/08/18_nrt/ga_ls7e_ard_provisional_3-2-1_103076_2021-08-18_nrt.odc-metadata.yaml --confirm-ignore-lineage
datacube dataset add https://data.dea.ga.gov.au/baseline/ga_ls8c_ard_provisional_3/107/073/2021/08/22_nrt/ga_ls8c_ard_provisional_3-2-1_107073_2021-08-22_nrt.odc-metadata.yaml --confirm-ignore-lineage

# s2 provisional datasets
datacube dataset add https://data.dea.ga.gov.au/baseline/ga_s2am_ard_provisional_3/52/LHL/2021/08/29_nrt/20210829T030536/ga_s2am_ard_provisional_3-2-1_52LHL_2021-08-29_nrt.odc-metadata.yaml --confirm-ignore-lineage
datacube dataset add https://data.dea.ga.gov.au/baseline/ga_s2bm_ard_provisional_3/55/LDE/2021/08/29_nrt/20210829T015117/ga_s2bm_ard_provisional_3-2-1_55LDE_2021-08-29_nrt.odc-metadata.yaml --confirm-ignore-lineage
