from fileinput import filename
import requests
import PyPDF2
import io
from pydantic import BaseModel
from typing import Optional
import json
from enum import Enum
import tabula
import os
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)
import pandas as pd


BASE_URL = "https://static.portaldasfinancas.gov.pt/app/devedores_static/{filename}"


class Step(BaseModel):
    start: int
    end: Optional[int] = None


class DebtorType(str, Enum):
    COLECTIVE = "colectivo"
    SINGULAR = "singular"


class Debtor(BaseModel):
    name: str
    step_text: str
    step: Step


class SingularDebtor(Debtor):
    nif: int


class ColectiveDebtor(Debtor):
    nipc: int


RAW_FILES_PATH = "files"
JSON_FILES_PATH = "data"


def dump_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)


def try_int(value: str):
    try:
        return int(value)
    except:
        return None


class NoDataException(Exception):
    pass


def get_step(response_content: bytes) -> tuple[str, Step, DebtorType]:
    pdf_file = io.BytesIO(response_content)
    reader = PyPDF2.PdfReader(pdf_file)
    page = reader.pages[0]
    text_lines = page.extract_text().split("\n")
    if "singulares" in text_lines[0].lower():
        debtor_type = DebtorType.SINGULAR
    else:
        debtor_type = DebtorType.COLECTIVE

    step_text_list = [t for t in text_lines if "devedores" in t.lower()]
    if step_text_list:
        step_text = (
            step_text_list[0]
            .lower()
            .replace("devedores de", "")
            .strip()
        )
        clean_step_text = step_text.replace("€", "").replace(".", "").strip()
        if "mais de" in clean_step_text:
            step_start = clean_step_text.split("mais de")[-1].strip()
            step = Step(start=int(step_start))
        else:
            step_start, step_end = clean_step_text.split(" a ")
            step = Step(start=int(step_start), end=int(step_end))
        return step_text, step, debtor_type

    raise NoDataException


def is_decimal(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def is_number(value):
    return str(value).isnumeric() or is_decimal(value)


def extract_string(row: pd.Series, key: str = "NOME"):
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


def extract_number(row: pd.Series, key: str = "NIF"):
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


def parse_singular_debtor(row: pd.Series, step_text: str, step: Step) -> SingularDebtor:
    nif = extract_number(row, "NIF")
    name = extract_string(row, "NOME")

    return SingularDebtor(nif=nif, name=name, step_text=step_text, step=step)


def parse_colective_debtor(row: pd.Series, step_text: str, step: Step) -> ColectiveDebtor:
    nipc = extract_number(row, "NIPC")
    name = extract_string(row, "DESIGNAÇÃO")

    return ColectiveDebtor(nipc=nipc, name=name, step_text=step_text, step=step)


def parse_data(filepath: str) -> list[SingularDebtor | ColectiveDebtor]:
    with open(filepath, "rb") as f:
        content = f.read()

    step_text, step, debtor_type = get_step(content)
    dfs = tabula.read_pdf(filepath, pages="all")

    df = pd.concat(dfs)

    parser = (
        parse_singular_debtor
        if debtor_type == DebtorType.SINGULAR
        else parse_colective_debtor
    )
    debtors: list[Debtor] = []
    for _, row in df.iterrows():
        debtor = parser(row,step_text, step)
        debtors.append(debtor)
    return debtors


def dump_file(filename, content: str):
    filepath = os.path.join(RAW_FILES_PATH, filename)
    with open(filepath, "wb") as f:
        f.write(content)


def fetch_file_data(base_filename: str):
    count = 1
    while True:
        filename = base_filename.format(n=count)
        url = BASE_URL.format(filename=filename)
        response = requests.get(url)
        if response.status_code == 404:
            break
        dump_file(filename, response.content)
        count += 1


def fetch_data():
    fetch_file_data("listaFS{n}.pdf")
    fetch_file_data("listaFC{n}.pdf")


def process_files():
    for filename in os.listdir(RAW_FILES_PATH):
        source = os.path.join(RAW_FILES_PATH, filename)
        dest = os.path.join(JSON_FILES_PATH, filename.replace(".pdf", ".json"))
        try:
            debtors = parse_data(source)
        except NoDataException:
            continue

        dump_json(dest, [d.model_dump() for d in debtors])


def setup():
    os.makedirs(RAW_FILES_PATH, exist_ok=True)
    os.makedirs(JSON_FILES_PATH, exist_ok=True)

def join_files():
    singular_debtors = []
    colective_debtors = []
    for filename in os.listdir(JSON_FILES_PATH):
        filepath = os.path.join(JSON_FILES_PATH, filename)
        with open(filepath) as f:
            if "FS" in filename:
                singular_debtors.extend(json.load(f))
            elif "FC" in filename:
                colective_debtors.extend(json.load(f))        

    data = {
        "singular_debtors": singular_debtors,
        "colective_debtors": colective_debtors
    }
    dest = os.path.join(JSON_FILES_PATH, "debtors.json")
    dump_json(dest, data)

def main():
    setup()
    fetch_data()
    process_files()
    join_files()


if __name__ == "__main__":
    main()
