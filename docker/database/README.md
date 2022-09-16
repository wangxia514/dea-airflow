# How to create a new database from scratch

```
docker-compose up -d
docker-compose run index datacube system init
docker-compose run index bash dbsetup.sh

 docker exec -e PGPASSWORD=opendatacubepassword database-postgres-1 bash -c 'pg_dump -U opendatacubeusername -d opendatacube -p 5432 -h localhost' > opendatacube.sql
```

