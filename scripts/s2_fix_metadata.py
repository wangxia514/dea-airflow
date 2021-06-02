from odc.aio import S3Fetcher, s3_find_glob
import boto3
import yaml
from pathlib import Path
from eodatasets3.model import AccessoryDoc, DatasetDoc, ProductDoc
from eodatasets3 import DatasetAssembler, documents, images, serialise, validate
import os
import json
from eodatasets3.stac import to_stac_item
from eodatasets3.scripts.tostac import json_fallback
from odc.aws import s3_client, s3_dump
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import as_completed
import click
from tqdm import tqdm
from c3_to_s3_rolling import publish_sns, get_common_message_attributes



NCI_DIR = "/g/data/if87/datacube/002/S2_MSI_ARD/packaged"


@click.command()
@click.argument('date', type=str, nargs=1)
@click.option('--workers', type=int, default=4)
def fix_metadata(date, workers):
    uri = f"s3://dea-public-data/baseline/s2a_ard_granule/{date}/**/*.yaml"

    fetcher = S3Fetcher(aws_unsigned=True)
    s3_obj_stream = s3_find_glob(uri, skip_check=True, s3=fetcher)
    s3_url_stream = (o.url for o in s3_obj_stream)
    data_stream = list(fetcher(s3_url_stream))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(process_dataset, s3_obj) for s3_obj in data_stream]
        
        for future in as_completed(futures):
            if future.exception() is not None:
                raise future.exception()

    
def process_dataset(s3_obj):
    
    s3_eo3_path = s3_obj.url
    s3_stac_path = s3_eo3_path.replace("eo3", "stac")
    s3_stac_path = s3_stac_path.replace("yaml", "json")
    s3_path = s3_eo3_path.replace("eo3-ARD-METADATA.yaml", "")
    granule = os.path.join(*s3_eo3_path.split('/')[5:-1])
    nci_path = os.path.join(NCI_DIR, *s3_eo3_path.split('/')[5:-1], "ARD-METADATA.yaml")
    
    if "S2A_OPER_MSI_ARD" in granule:
        platform = "SENTINEL_2A"
    elif "S2B_OPER_MSI_ARD" in granule:
        platform = "SENTINEL_2B"
    else:
        raise ValueError(
            f"Expected granule id to contain either 'S2A_OPER_MSI_ARD' or 'S2B_OPER_MSI_ARD', found '{granule}'"
        )
    
    with open(nci_path) as fin:
        eo_metadata = yaml.safe_load(fin)
    
    eo3_metadata = yaml.safe_load(s3_obj.data)
    
    eo3_metadata["properties"]["odc:region_code"] = eo_metadata["provider"]["reference_code"]
    eo3_metadata["properties"]["gqa:cep90"] = eo_metadata["gqa"]["residual"]["cep90"]
    eo3_metadata["properties"]["gqa:error_message"] = eo_metadata["gqa"]["error_message"]
    eo3_metadata["properties"]["gqa:final_gcp_count"] = eo_metadata["gqa"]["final_gcp_count"]
    eo3_metadata["properties"]["gqa:ref_source"] = eo_metadata["gqa"]["ref_source"]
    eo3_metadata["properties"]["sentinel:datatake_start_datetime"] = granule.split("_")[-4]
    eo3_metadata["properties"]["eo:platform"] = platform
    
    for key in ["abs_iterative_mean", "abs", "iterative_mean", "iterative_stddev", "mean", "stddev"]:
        eo3_metadata["properties"][f"gqa:{key}_xy"] = eo_metadata["gqa"]["residual"][key]["xy"]

    eo3 = serialise.from_doc(eo3_metadata)
    stac = to_stac_item(
        eo3,
        stac_item_destination_url=s3_stac_path,
        odc_dataset_metadata_url=s3_eo3_path,
        dataset_location=s3_path,
    )
    stac_dump = json.dumps(stac, default=json_fallback, indent=4)
    eo3_dump = yaml.safe_dump(eo3_metadata, default_flow_style=False)

    s3_dump(
        eo3_dump, 
        s3_eo3_path, 
        ACL="bucket-owner-full-control",
        ContentType="text/vnd.yaml",
    )

    s3_dump(
        stac_dump, 
        s3_stac_path, 
        ACL="bucket-owner-full-control",
        ContentType="application/json"
    )


if __name__ == "__main__":
    fix_metadata()