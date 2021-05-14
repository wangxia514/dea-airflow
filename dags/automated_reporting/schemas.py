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
                            {"name": "product"},
                            {"name": "sat_acq_date"},
                            {"name": "processing_date"},
                            {"name": "last_updated"},
                        ],
                    }
                ],
            }
        ],
    }
}
