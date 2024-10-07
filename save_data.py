import json
from load_data import load_data
from DATA.CONSTANTS import data_path

from init_logger import setup_logger
logger = setup_logger("save_data")


def save_data(knives=None,graved=None,found=None):
    k,g,f = load_data()
    data = {
        "NUMBER": k,
        "GRAVED": g,
        "FOUND": f,
    }
    if knives != None:
        data["NUMBER"] = knives
    if graved != None:
        data["GRAVED"] = graved
    if found != None:
        data["FOUND"] = found

    with open(data_path, "w") as f:
        json.dump(data, f, indent=4)
    
    print("save_data : data saved successfully")
save_data()