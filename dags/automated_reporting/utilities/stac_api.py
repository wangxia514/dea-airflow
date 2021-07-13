"""
Utilities to query USGS Stac API
"""
import requests
import json

serviceUrl = "https://landsatlook.usgs.gov/sat-api/collections/landsat-c2l1/items"
collectionCategory = "RT"
bbox = [106, -47, 160, -5]


def sendRequest(url, data, logger):
    """
    Send HTTPS Request
    :param url: URL of stac API
    :param data: Search Criteria
    :param logger: Logging
    :return: JSON output
    """
    jsonData = json.dumps(data)
    response = requests.post(url, jsonData)
    logger.debug("Response - {}".format(response))
    output = json.loads(response.text)
    logger.debug("Output - {}".format(output))

    try:
        httpStatusCode = response.status_code
        if httpStatusCode == 404:
            logger.error("404 Not Found")
            exit()
        elif httpStatusCode == 401:
            logger.error("401 Unauthorized")
            exit()
        elif httpStatusCode == 400:
            logger.error("Error Code", httpStatusCode)
            exit()
        elif httpStatusCode == 502:
            logger.error("Internal Server Error", httpStatusCode)
            exit()
    except Exception as e:
        response.close()
        logger.error(e)
        exit()
    response.close()

    return output


def landsat_search_stac(logger, mission, startDate, endDate):
    """
    Conduct the search on the stac api
    :param serviceUrl: Stac API URL
    :param logger:
    :param mission: the mission to search for in the collection
    :return: response from stac API
    """
    searchParameters = {
        "page": 1,
        "limit": 10000,
        "bbox": bbox,
        "query": {
            "landsat:collection_category": {"eq": "{}".format(collectionCategory)},
            "platform": {"eq": "{}".format(mission)},
        },
        "time": "{0}T/{1}T".format(startDate, endDate),
    }
    response = sendRequest(serviceUrl, searchParameters, logger)
    return response


def collect_stac_api_results(output):
    """
    Collectio STAC API Results
    :param output: The Stac API output
    :return: matrix of relevant results
    """
    returned = int(output["meta"]["returned"])

    stacApiMatrix = [[]]

    for i in range(0, returned):
        stacApiMatrix.append(
            [
                output["features"][i]["properties"]["landsat:scene_id"],
                output["features"][i]["properties"]["landsat:wrs_path"],
                output["features"][i]["properties"]["landsat:wrs_row"],
                output["features"][i]["properties"]["landsat:collection_category"],
                output["features"][i]["properties"]["landsat:collection_number"],
                output["features"][i]["properties"]["datetime"],
            ]
        )

    stacApiMatrix.pop(0)
    return stacApiMatrix
