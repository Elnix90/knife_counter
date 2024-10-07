import json
import os

data_path = "DATA/data.json"


from init_logger import setup_logger
logger = setup_logger("load_data")


def load_data():
    if not os.path.exists(data_path):
        data = {
            "NUMBER": 0,
            "GRAVED": [],
            "FOUND": []
        }
        with open(data_path, "w") as f:
            json.dump(data, f, indent=4)
        logger.warning("Load data: file not found, creating default data")
    else:

        with open(data_path, "r") as f:
            data = json.load(f)
        logger.info("Load data: data loaded successfully")
    

    KNIFE_NUMBER = data.get("NUMBER", 0)
    GRAVED_LOGS = data.get("GRAVED", [])
    FOUND_LOGS = data.get("FOUND", [])

    return KNIFE_NUMBER, GRAVED_LOGS, FOUND_LOGS
