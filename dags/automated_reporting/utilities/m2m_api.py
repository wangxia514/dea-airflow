"""
Utilities to query USGS M2M API. Use `get` or `get_matrix` as the public methods of this
module.
"""
import json
import logging
import pytz
from datetime import datetime as dt, timedelta as td

import requests

log = logging.getLogger("airflow.task")


class USGSM2MError(Exception):
    """
    Custom error for USGS M2M
    """

    pass


serviceUrl = "https://m2m.cr.usgs.gov/api/api/json/stable/"

# Base query parameters, modified before calls are made
spatialFilter = {
    "filterType": "mbr",
    "lowerLeft": {"latitude": -47, "longitude": 106},
    "upperRight": {"latitude": -5, "longitude": 160},
}

metadataFilter = {"filterType": "value", "filterId": "5e81f14fff5055a3", "value": "RT"}

payload = {
    "datasetName": None,
    "maxResults": 100,
    "startingNumber": None,
    "metadataType": "full",
    "sceneFilter": {
        "metadataFilter": metadataFilter,
        "spatialFilter": spatialFilter,
        "acquisitionFilter": None,
    },
}


def _sendRequest(url, data, apiKey=None):
    """
    Function to return JSON data from API
    """
    json_data = json.dumps(data)

    if apiKey == None:
        response = requests.post(url, json_data)
    else:
        headers = {"X-Auth-Token": apiKey}
        response = requests.post(url, json_data, headers=headers)

    try:
        httpStatusCode = response.status_code
        if response == None:
            log.error("No output from service")
            raise USGSM2MError("No output from service")
        output = json.loads(response.text)
        if output["errorCode"] != None:
            log.error(output["errorCode"], "- ", output["errorMessage"])
            raise USGSM2MError(output["errorCode"], "- ", output["errorMessage"])
        if httpStatusCode == 404:
            log.error("404 Not Found")
            raise USGSM2MError("404 Not Found")
        elif httpStatusCode == 401:
            log.error("401 Unauthorized")
            raise USGSM2MError("401 Unauthorized")
        elif httpStatusCode == 400:
            log.error("Error Code: 400")
            raise USGSM2MError("Error Code: 400")
    except Exception as e:
        import traceback

        log.error(traceback.format_exc())
        response.close()
        log.error(e)
        raise USGSM2MError("Unhandled USGS M2M Api Error")
    response.close()

    return output["data"]


def _get_metadata(result, fieldName):
    """Extract a result from metadata, by name"""
    for data in result["metadata"]:
        if fieldName == data["fieldName"]:
            return data["value"]
    return None


def _center_time(result):
    """Calculate the center time of the acquisition from metadata"""
    start = dt.strptime(
        _get_metadata(result, "Start Time")[:-1], "%Y:%j:%H:%M:%S.%f"
    ).timestamp()
    end = dt.strptime(
        _get_metadata(result, "Stop Time")[:-1], "%Y:%j:%H:%M:%S.%f"
    ).timestamp()
    center = dt.fromtimestamp((start + end) / 2).replace(tzinfo=pytz.utc)
    return center


def _published_time(result):
    """Get a Python datetime of when the record was published by USGS"""
    return (
        dt.strptime(result["publishDate"] + "00", "%Y-%m-%d %H:%M:%S%z")
        .astimezone(pytz.utc)
        .isoformat()
    )


def _path_row(result):
    """Get a combined path row from metadata i.e 096_124"""
    return (
        _get_metadata(result, "WRS Path").strip()
        + "_"
        + _get_metadata(result, "WRS Row").strip()
    )


def _process_results(results):
    """
    Extract a group pof results from response and store in a list of dictionaries
    """
    output = []
    for result in results:
        if result["displayId"].startswith("LC08"):
            platform = "ls8"
        elif result["displayId"].startswith("LE07"):
            platform = "ls7"
        else:
            platform = None
        item = dict(
            id=result["entityId"],
            acq_time=_center_time(result).isoformat(),
            l1_time=_published_time(result),
            display_id=result["displayId"],
            cloud_cover=result["cloudCover"],
            collect_cat=_get_metadata(result, "Collection Category"),
            collect_num=_get_metadata(result, "Collection Number"),
            wrs2=_path_row(result),
            platform=platform,
        )
        output.append(item)
    return output


def get(start_time, days, dataset, credentials):
    """
    Login to USGS M2M Api and query based on a timeframe, dataset id, and spatial
    bound ing box.
    """

    # Login to API
    apiKey = _sendRequest(serviceUrl + "login", credentials)

    # Modify payload with specific parameters
    payload["datasetName"] = dataset
    payload["startingNumber"] = 1
    payload["sceneFilter"]["acquisitionFilter"] = dict(
        end=start_time.strftime("%Y-%m-%d"),
        start=(start_time - td(days=days)).strftime("%Y-%m-%d"),
    )

    # Log the query parameters
    log.debug("M2M Query Parameters")
    log.debug(json.dumps(payload, indent=4))

    # List to store results
    results = list()
    # Make initial query and extract results to list
    scenes = _sendRequest(serviceUrl + "scene-search", payload, apiKey)
    results += _process_results(scenes.get("results", []))

    # Store the total number of results to check after completion
    expected_results_len = scenes["totalHits"]

    # Using total number of hits, generate further requests
    # No multi-threading here, USGS doesn't allow concurrent connections
    #   from the same account
    offsets = [offset for offset in range(101, scenes["totalHits"], 100)]
    for offset in offsets:
        # Set the offset in the query payload
        payload["startingNumber"] = offset
        # Make api queries and extract results to list
        scenes = _sendRequest(serviceUrl + "scene-search", payload, apiKey)
        results += _process_results(scenes.get("results", []))

    # If the  list doesn't atch the number of expected results, raise an error
    # There could be a situation were this is more if new datastsets are added
    #   during the loop above
    if len(results) < expected_results_len:
        raise USGSM2MError("Results count doesn't match expected results count")
    return results
