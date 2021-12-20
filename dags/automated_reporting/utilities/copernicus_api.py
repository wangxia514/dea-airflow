"""
Utilities for copernicus api (scihub) queries
"""

import logging
import requests
from concurrent import futures
from datetime import timezone, timedelta, datetime as dt

from automated_reporting.utilities import helpers
from automated_reporting.aux_data import aoi

log = logging.getLogger("airflow.task")


def query(execution_date, days, copernicus_api_creds):
    """Query Copernicus/Scihub for a product type, date range and area of interest"""

    execution_date = helpers.python_dt(execution_date)

    producttype = "S2MSI1C"
    aoi_polygon = aoi.AOI_POLYGON

    # base Copernicus API url and query, needs query arguments inserted
    cop_url = 'https://scihub.copernicus.eu/dhus/search?q=ingestiondate:[{} TO {}] AND \
            producttype:{} AND footprint:"Intersects({})"&start={}&rows=100&format=json'

    # gets dates in a format suitable for Copernicus API
    cop_start_time = (execution_date - timedelta(days=days)).astimezone(
        tz=timezone.utc
    ).replace(tzinfo=None).isoformat() + "Z"
    cop_end_time = (
        execution_date.astimezone(tz=timezone.utc).replace(tzinfo=None).isoformat()
        + "Z"
    )

    log.info(
        "Querying Copernicus API between {} - {} for {}".format(
            cop_start_time, cop_end_time, producttype
        )
    )

    # Helper functions
    def get(url):
        """
        Perform a GET to copernicus api for paged inventory data
        """
        return requests.get(
            url,
            auth=(copernicus_api_creds["user"], copernicus_api_creds["password"]),
        )

    def format_url(offset=0):
        """
        Format url with query arguments
        """
        return cop_url.format(
            cop_start_time, cop_end_time, producttype, aoi_polygon, offset
        )

    def get_entry_val(entry, data_type, name):
        """
        Extract a value from entry section of response
        """
        for val in entry[data_type]:
            if val["name"] == name:
                return val["content"]
        return None

    expected_products = []
    start_time = dt.now()

    # make a first api call with a zero offset
    resp = get(format_url(0))
    if resp.ok:

        # start a list of responses
        responses = [resp]

        # use count from first response to build a list of urls for
        # multi-threaded download
        count = int(resp.json()["feed"]["opensearch:totalResults"])
        log.info("Downloading: {}".format(count))
        urls = [format_url(offset) for offset in range(100, count, 100)]

        # populate responses list with a multithreaded download
        with futures.ThreadPoolExecutor(max_workers=6) as executor:
            res = executor.map(get, urls)
            responses += list(res)

        # check responses and extract result in expected_products list
        for resp in responses:
            if resp.ok:
                data = resp.json()["feed"]
                if type(data["entry"]) == dict:
                    data["entry"] = [data["entry"]]
                for entry in data["entry"]:
                    granule_id = get_entry_val(entry, "str", "granuleidentifier")
                    row = {
                        "uuid": entry["id"],
                        "granule_id": granule_id,
                        "region_id": get_entry_val(entry, "str", "tileid"),
                        "sensor": granule_id[:3].lower(),
                        "identifier": get_entry_val(entry, "str", "identifier"),
                    }
                    expected_products.append(row)
            else:
                raise Exception("Sentinel API Failed: {}".format(resp.status_code))
        log.info("Downloaded: {}".format(len(expected_products)))

        # check that the inventory list is the same length as the expected count
        if count != len(expected_products):
            raise Exception("Sentinel API Failed: products missing from download")
    else:
        raise Exception("Sentinel API Failed: {}".format(resp.status_code))

    log.info(
        "Copernicus API download completed in {} seconds".format(
            (dt.now() - start_time).total_seconds()
        )
    )
    return expected_products
