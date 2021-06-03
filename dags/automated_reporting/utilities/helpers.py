"""
Helper functions for automated reporting dags
"""

from datetime import timezone, datetime as dt

ZERO_TS = dt(1970, 1, 1, tzinfo=timezone.utc)


def db_has_object(rep_cursor, sql, query_args):
    """
    Tests if an SQL query returns any rows, returns boolean
    """
    rep_cursor.execute(sql, query_args)
    if rep_cursor.rowcount == 0:
        return False
    return True


def python_dt(airflow_dt):
    """
    Convert Airflow datetime (Pendulum) to regular python datetime
    """
    return dt(
        airflow_dt.year,
        airflow_dt.month,
        airflow_dt.day,
        airflow_dt.hour,
        airflow_dt.minute,
        airflow_dt.second,
        airflow_dt.microsecond,
        tzinfo=airflow_dt.tz,
    )
