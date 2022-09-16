#!/bin/bash

# For creating opendatacube.sql dump

### Add metadata ###

datacube metadata add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/product_metadata/eo3_landsat_ard.odc-type.yaml # for provisional ard

### add products

# provisional products
datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/baseline_satellite_data/provisional/ard_ls7_provisional.odc-product.yaml # ls7 provision products
datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/baseline_satellite_data/provisional/ard_ls8_provisional.odc-product.yaml # ls8 provisional products
datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/baseline_satellite_data/provisional/ard_s2a_provisional.odc-product.yaml # s2a provisional products
datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/baseline_satellite_data/provisional/ard_s2b_provisional.odc-product.yaml # s2b provisional products

### add limited datasets ###

# ga_ls7/ls8 provisional datasets
datacube dataset add https://data.dea.ga.gov.au/baseline/ga_ls7e_ard_provisional_3/104/076/2022/08/23_nrt/ga_ls7e_ard_provisional_3-2-1_104076_2022-08-23_nrt.odc-metadata.yaml --confirm-ignore-lineage
datacube dataset add https://data.dea.ga.gov.au/baseline/ga_ls8c_ard_provisional_3/107/073/2022/08/25_nrt/ga_ls8c_ard_provisional_3-2-1_107073_2022-08-25_nrt.odc-metadata.yaml --confirm-ignore-lineage

# s2 provisional datasets
datacube dataset add https://data.dea.ga.gov.au/baseline/ga_s2am_ard_provisional_3/52/LHL/2022/08/24_nrt/20220824T025056/ga_s2am_ard_provisional_3-2-1_52LHL_2022-08-24_nrt.odc-metadata.yaml --confirm-ignore-lineage
datacube dataset add https://data.dea.ga.gov.au/baseline/ga_s2bm_ard_provisional_3/55/LDE/2022/08/31_nrt/20220831T012856/ga_s2bm_ard_provisional_3-2-1_55LDE_2022-08-31_nrt.odc-metadata.yaml --confirm-ignore-lineage
