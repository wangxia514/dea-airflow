## Utility
Pre-defined workflow dags to support ad-hoc need.

### Add product index update
Use case: Need to add a new product to database and/or add datasets to the product.

Scope: add product, add dataset to product and update explorer.

### Batch indexing ows and explorer update
Use case: for new dataset produced where the product is in the database and ows layer is established.

Scop: Some well established product have new datasets produced after its indexed and they need to be added to the database, ows and explorer.

### ows update
Use case: For situation where ows product looks out of date

scope: Only updates ows

### explorer update
Use case: For situation where explorer product look out of date

Scope: Only updates explorer

### db to s3
Use case: Need a live database dump for restoring for local testing

Scope: create a copy of database and store in s3 weekly or on demand.
