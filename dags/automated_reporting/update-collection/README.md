# Update-collection component 
Component to use after a new collection list is added

## Steps to add a new collection
### Prerequisite
	Update the colletion file here
	https://github.com/GeoscienceAustralia/dea-config/blob/master/workspaces/collections.csv
### Run update-collection DAG

	The DAG is present here https://airflow.dev.dea.ga.gov.au/tree?dag_id=k8s_dea_access_collection_updater

	This DAG does the following
		1. Download the collections.csv from the master branch of dea-config/workspaces
		2. Run csv2collections.py to generate JSON files
		3. Calls generateAuthToken to create the bearer token
		4. Call RESTO API to register the new collection
			if the collection already exists, it does an upate
### Update the "model" code under addons if neccessary
	https://github.com/jjrom/dea-access/blob/develop/components/resto-dea/addons/resto-addon-dea/src/DEAModel.php#L88
