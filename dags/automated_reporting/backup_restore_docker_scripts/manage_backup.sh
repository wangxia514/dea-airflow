date_diff=30
p_dataset_date=`date --date="$EXECUTION_DATE -$date_diff day" +%Y-%m-%d`
echo $p_dataset_date
day=`echo $p_dataset_date | cut -f3 -d'-'`
echo $day
if [ "$day" != "01" ]
then
        echo "Removig backup for date $p_dataset_date"
        aws s3 rm s3://$REPORTING_BUCKET/$p_dataset_date/ --recursive
else
        echo "Old backup points to 1st day of a month $p_dataset_date"
        echo "So NO Action as we want to retain 1st day of month backups"
fi
