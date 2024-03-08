import json
import os
import datetime

from src.config import JSON_FILES_PATH, MAIN_FILE_NAME
from src.utils import dump_json


def join_files():
    """
    Joins the singular and colective debtors json files into a single json file
    """
    singular_debtors = []
    colective_debtors = []
    last_updated = None
    for filename in os.listdir(JSON_FILES_PATH):
        filepath = os.path.join(JSON_FILES_PATH, filename)
        with open(filepath) as f:
            if "FS" not in filename and "FC" not in filename:
                continue
            data: dict = json.load(f)

            # keep the earliest last_updated date
            file_last_updated = data.get("last_updated")
            file_last_updated = datetime.date.fromisoformat(file_last_updated)
            if last_updated is None:
                last_updated = file_last_updated
            elif file_last_updated < last_updated:
                last_updated = file_last_updated
            
            debtors_data = data.get("debtors")
            # append the debtors to the corresponding list
            if "FS" in filename:
                singular_debtors.extend(debtors_data)
            elif "FC" in filename:
                colective_debtors.extend(debtors_data)

    data = {
        "last_updated": last_updated.isoformat(),
        "singular_debtors": singular_debtors,
        "colective_debtors": colective_debtors,
    }
    dest = os.path.join(JSON_FILES_PATH, MAIN_FILE_NAME)
    dump_json(dest, data)
