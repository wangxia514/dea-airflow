#!/bin/bash
#
# Copyright 2018 Jérôme Gasperi
#
# Licensed under the Apache License, version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#   https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

###### DO NOT TOUCH DEFAULT VALUES ########
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
############################################
ABS_SCRIPTS_PATH=$(cd -P -- "$(dirname -- "$0")" && printf '%s\n' "$(pwd -P)")
DATA_DIR=${ABS_SCRIPTS_PATH}/../../data

#Read CSV file from github
#wget https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/workspaces/collections.csv
wget https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/collections-update/workspaces/collections.csv

env 

mkdir -p ./data/collections

#Run CSV to collections to generate json files
./csv2collections.py

#Generate Bearer token based on secrets from DAG/K8s
TOKEN=`./generateAuthToken.py`

#For each collection item post collection to Resto
for collection in ./data/collections/*.json; do
    COLLECTION_ID=$(grep \"id\"\: ${collection} | awk -F\: '{print $2}' |  sed 's/\"//g' | sed 's/,//g' | awk '{print $1}')
    HTTP_STATUS=$(curl --header "Authorization: Bearer ${TOKEN}" --write-out %{http_code} --silent --output /dev/null "https://${RESTO_URL}/collections/${COLLECTION_ID}")
    echo "Collection id ${COLLECTION_ID} Status ${HTTP_STATUS}"
    if [ "${HTTP_STATUS}" != "200" ]; then
        echo -e "[INFO] ${GREEN}Create${NC} collection ${COLLECTION_ID}"
        curl -X POST --header "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" -d @${collection} "https://${RESTO_URL}/collections"
    else
        echo -e "[INFO] ${GREEN}Update${NC} collection ${COLLECTION_ID}"
        curl -X PUT --header "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" -d @${collection} "https://${RESTO_URL}/collections/${COLLECTION_ID}"
    fi
    echo ""
done
