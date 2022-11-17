"""
# list of product names for webapplication to update
here is the complete list of OWS product: https://github.com/GeoscienceAustralia/dea-config/blob/master/dev/services/wms/inventory.json
complete list of Explorer products can be found here: https://explorer.dev.dea.ga.gov.au/products
"""

# ows layer product to be updated
OWS_UPDATE_LIST = (
    "s2_nrt_granule_nbar_t",
    "s2_ard_granule_nbar_t",
    "ga_ls_wo_3",
    "ga_s2_wo_3",
    "ga_ls_fc_3",
    "ga_ls_ard_3",
    "ga_ls_ard_provisional_3",
    "s2_nrt_provisional_granule_nbar_t",
    "ga_s2_ba_provisional_3",
    "ga_s2_wo_provisional_3",
    "ga_s2m_ard_3",
)

EXPLORER_UPDATE_LIST = (
    "s2a_nrt_granule",
    "s2b_nrt_granule",
    "s2a_ard_granule",
    "s2b_ard_granule",
    "ga_ls_wo_3",
    "ga_s2_wo_3",
    "ga_ls_fc_3",
    "ga_ls5t_ard_3",
    "ga_ls7e_ard_3",
    "ga_ls8c_ard_3",
    "ga_ls7e_ard_provisional_3",
    "ga_ls8c_ard_provisional_3",
    "ga_s2am_ard_provisional_3",
    "ga_s2bm_ard_provisional_3",
    "ga_s2_ba_provisional_3",
    "ga_s2_wo_provisional_3",
    "ga_s2am_ard_3",
    "ga_s2bm_ard_3",
)
