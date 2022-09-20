# How to create a new database from scratch

```
docker-compose up -d
docker-compose exec index datacube system init
docker-compose exec index bash dbsetup.sh

docker-compose exec -e PGPASSWORD=opendatacubepassword postgres bash -c 'pg_dump -U opendatacubeusername -d opendatacube -p 5432 -h localhost' > opendatacube.sql
```

