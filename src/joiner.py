import datetime
import os

from src.exceptions import NoDataException
from src.models import DebtorsData
from src.utils import dump_json, load_json


def join_files(directory: str, destination_file: str) -> DebtorsData:
    """
    Joins the singular and colective debtors json files into a single json file
    """
    singular_debtors = []
    colective_debtors = []
    last_updated = None
    for filename in os.listdir(directory):
        if "FS" not in filename and "FC" not in filename:
            continue
        filepath = os.path.join(directory, filename)
        data = load_json(filepath)
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

    if not singular_debtors and not colective_debtors:
        raise NoDataException(
            "No debtors json files found - ensure the files are named correctly (with 'FS' for singular and 'FC' for colective) and in the correct directory."
        )

    data = DebtorsData(
        last_updated=last_updated.isoformat() if last_updated else None,
        singular_debtors=singular_debtors,
        colective_debtors=colective_debtors,
    )

    dest = os.path.join(directory, destination_file)
    dump_json(dest, data.model_dump())
    return data
