IMAGE_ECR = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com"

NODE_AFFINITY = {
    "nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [
                {
                    "matchExpressions": [
                        {
                            "key": "nodetype",
                            "operator": "In",
                            "values": [
                                "ondemand",
                            ],
                        }
                    ]
                }
            ]
        }
    }
}

# OWS pod specific configuration
OWS_CFG_PATH = "/env/config/ows_refactored/ows_root_cfg.py"
OWS_CFG_MOUNT_PATH = "/env/config"
OWS_CFG_PATH = OWS_CFG_MOUNT_PATH + "/ows_cfg.py"
OWS_CFG_IMAGEPATH = "/opt/dea-config/dev/services/wms/ows_refactored"
OWS_PYTHON_PATH = "/env/config"
OWS_DATACUBE_CFG = "config.ows_cfg.ows_cfg"
