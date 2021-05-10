import requests
import json
import csv

#read from github dea-config the latest csv file
url = 'https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/workspaces/collections.csv'
r = requests.get(url, allow_redirects=True)

#read the name and the count columns
open('collections.csv', 'wb').write(r.content)
with open('collections.csv', 'rt') as csvfile:
    # get number of columns
    for line in csvfile.readlines():
        array = line.split(',')

    num_columns = len(array)
    csvfile.seek(0)
    reader = csv.reader(csvfile, delimiter=',')
    next(reader, None)  # skip the headers
    included_cols = [5]
    content= []
    for row in reader:
      if row[5] != 'None':
          content.append(row[5])

print(content)
