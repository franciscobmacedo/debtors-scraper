import json
import pandas as pd


def dump_json(file: str, data: dict | list):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)


def try_int(value: str):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def is_decimal(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def is_number(value):
    if isinstance(value, bool):
        return False
    try:
        return str(value).isnumeric() or is_decimal(value)
    except (ValueError, TypeError):
        return False


def extract_string(row: pd.Series, key: str):
    """
    Extracts a string value from a pandas Series object based on the specified key.
    If the value doesn't match the expected type (string), try the other cells
    """
    name = row[key]
    if pd.isna(name) or is_number(name):
        for cell in row:
            if pd.isna(cell):
                continue
            if isinstance(cell, str) and not is_number(cell):
                return cell
    return name


def extract_number(row: pd.Series, key: str):
    """
    Extracts a numeric value from a pandas Series object based on the specified key.
    If the value doesn't match the expected type (int or float), try the other cells
    """
    nif = row[key]
    if pd.isna(nif):
        for cell in row:
            if pd.isna(cell):
                continue
            if isinstance(cell, str) and cell.isnumeric():
                return cell
            if isinstance(cell, int) or isinstance(cell, float):
                return cell
    return nif
