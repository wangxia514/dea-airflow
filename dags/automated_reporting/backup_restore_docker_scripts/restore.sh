result=`aws s3 cp s3://$REPORTING_BUCKET/$EXECUTION_DATE/$SCHEMA-dump.sql $SCHEMA-dump.sql`
exec_result=$?
if [ exec_result != 0 ]
then
    EXECUTION_DATE=`aws s3 ls s3://$REPORTING_BUCKET/ | tr -s ' ' ' ' | cut -f3 -d ' ' | cut -f1 -d '/' | tail -1`
    result=`aws s3 cp s3://$REPORTING_BUCKET/$EXECUTION_DATE/$SCHEMA-dump.sql $SCHEMA-dump.sql`
fi
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "DROP SCHEMA $SCHEMA CASCADE;"
psql -h $DB_HOST -U $DB_USER $DB_NAME < $SCHEMA-dump.sql
