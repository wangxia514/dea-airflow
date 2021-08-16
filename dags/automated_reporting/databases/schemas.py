"""
Schema defs for automated reporting dags
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

LATENCY_SCHEMA = {
    "database": {
        "name": "reporting",
        "schemas": [
            {
                "name": "landsat",
                "tables": [
                    {
                        "name": "derivative_latency",
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

USGS_COMPLETENESS_SCHEMA = {
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
            },
            {
                "name": "landsat",
                "tables": [
                    {
                        "name": "usgs_l1_nrt_c2_stac_listing",
                        "columns": [
                            {"name": "scene_id"},
                            {"name": "wrs_path"},
                            {"name": "wrs_row"},
                            {"name": "collection_category"},
                            {"name": "collection_number"},
                            {"name": "sat_acq"},
                        ],
                    }
                ],
            },
        ],
    }
}

HIGH_GRANULARITY_SCHEMA = {
    "database": {
        "name": "reporting",
        "schemas": [
            {
                "name": "high_granularity",
                "tables": [
                    {
                        "name": "dataset",
                        "columns": [
                            {"name": "id"},
                            {"name": "label"},
                            {"name": "product_def_id"},
                            {"name": "timestamp"},
                            {"name": "source_id"},
                            {"name": "region_id"},
                            {"name": "extra"},
                            {"name": "archived"},
                            {"name": "status_id"},
                            {"name": "created_at"},
                            {"name": "updated_at"},
                        ],
                    },
                    {
                        "name": "association",
                        "columns": [
                            {"name": "id"},
                            {"name": "upstream_id"},
                            {"name": "downstream_id"},
                        ],
                    },
                ],
            }
        ],
    }
}
