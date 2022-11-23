#!/usr/bin/env python3
# -*- coding: iso-8859-15 -*-
#
# Script to generate resto json file describing collections from DEA google drive spreadsheet referencing collections to ingest:
# https://docs.google.com/spreadsheets/d/1FEVotW1laipjstxZmO7weD1cAyA0KB6IRBH_HuHuvCM/edit#gid=0
#
#
import csv
import json
import os

# row[6] = title
# row[7] = desc

out_dir = './data/collections/'
csv_file = 'collections.csv'
COL_TEMPLATE = 'DEAModel_collection_template.json'
BAD_NAME = 'None'

# Optical collections inherit from DEAOpticalModel and not DEAModel
OPTICAL_COLLECTIONS = [
    'ga_ls5t_ard_3',
    'ga_ls7e_ard_3',
    'ga_ls8c_ard_3',
    'ga_ls_fc_3',
    'ga_ls_wo_3'
]

# reads collection template json

with open(csv_file) as csvfile:
    colreader = csv.reader(csvfile, delimiter=',', quotechar='"')
    next(colreader)
    for row in colreader:     
        with open(COL_TEMPLATE) as templ:
            col = json.load(templ)
        
            if row[5] == BAD_NAME:
                print("skipping collection without Explorer Title")
                continue

            # Optical collection has an OpticalModel
            if row[5] in OPTICAL_COLLECTIONS:
                col["model"] = "DEAOpticalModel"

            col["id"] = row[5]
            col["osDescription"]["en"]["LongName"] = row[2]
            col["osDescription"]["en"]["Description"] = row[3]

            # Append to properties
            properties = {
                "product_number": row[0]
            }
            if "properties" in col:
                col["properties"].update(properties)
            else:
                col["properties"] = properties
            # Append to links
            links = [
                {
                    "rel": "alternate",
                    "type": "text/html",
                    "title": "DEA Explorer collection",
                    "description": row[6],
                    "href": row[7]
                },
                {
                    "rel": "derived_from",
                    "type": "application/json",
                    "title": "DEA Explorer collection",
                    "description": row[6],
                    "href": row[8]
                }
            ]
            if "links" in col:
                col["links"].extend(links)
            else:
                col["links"] = links

            # Append to assets
            assets = {
                "thredds":{
                    "rel": "data",
                    "type": "application/xml",
                    "href": row[11]
                },
                "nci_location":{
                    "rel": "data",
                    "type": "application/octet-stream",
                    "href": "file://" + row[12]
                }
            }
            if "assets" in col:
                col["assets"].update(assets)
            else:
                col["assets"] = assets

            # Append to keywords
            keywords = [
                "label: " + row[4],
                "catalog: " + row[1]
            ]
            if "keywords" in col:
                col["keywords"].extend(keywords)
            else:
                col["keywords"] = keywords
            
            with open(os.path.join(out_dir, "%s.json" % col["id"]), 'w') as outfile:
                print("writing collection as json: %s" % col["id"])
                json.dump(col, outfile, indent=4)

print('Collection file(s) written to %s' % out_dir)
