"""
Schema definitions for automated reporting dags
"""

COMPLETENESS_SCHEMA = {
    "database": {
        "name": "reporting",
        "schemas": [
            {
                "name": "reporting",
                "tables": [
                    {
                        "name": "completeness",
                        "columns": [
                            {"name": "id"},
                            {"name": "geo_ref"},
                            {"name": "completeness"},
                            {"name": "expected_count"},
                            {"name": "actual_count"},
                            {"name": "product_id"},
                            {"name": "sat_acq_time"},
                            {"name": "processing_time"},
                            {"name": "last_updated"},
                        ],
                    },
                    {
                        "name": "completeness_missing",
                        "columns": [
                            {"name": "id"},
                            {"name": "completeness_id"},
                            {"name": "dataset_id"},
                            {"name": "last_updated"},
                        ],
                    },
                ],
            }
        ],
    }
}
