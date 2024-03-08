import io
import os
import datetime

import warnings
import PyPDF2
import tabula
from src.config import JSON_FILES_PATH, RAW_FILES_PATH
from src.exceptions import NoDataException
from src.models import (
    ColectiveDebtor,
    DebtorType,
    SingularDebtor,
    Step,
    Metadata,
)
from src.utils import dump_json, extract_number, extract_string

warnings.simplefilter(action="ignore", category=FutureWarning)
import pandas as pd


def parse_files():
    for filename in os.listdir(RAW_FILES_PATH):
        source = os.path.join(RAW_FILES_PATH, filename)
        dest = os.path.join(JSON_FILES_PATH, filename.replace(".pdf", ".json"))
        try:
            debtors, last_updated = parse_file(source)
        except NoDataException:
            continue

        file_data = {
            "last_updated": last_updated,
            "debtors": [d.model_dump() for d in debtors],
        }
        dump_json(dest, file_data)


def parse_file(
    filepath: str,
) -> tuple[list[SingularDebtor | ColectiveDebtor], str | None]:
    with open(filepath, "rb") as f:
        content = f.read()

    metadata = extract_metadata(content)
    dfs = tabula.read_pdf(filepath, pages="all")

    df = pd.concat(dfs)

    parser = (
        parse_singular_debtor
        if metadata.debtor_type == DebtorType.SINGULAR
        else parse_colective_debtor
    )
    debtors = [parser(row, metadata.step) for _, row in df.iterrows()]
    return debtors, metadata.last_updated


def extract_metadata(content: bytes) -> Metadata:
    pdf_file = io.BytesIO(content)
    reader = PyPDF2.PdfReader(pdf_file)
    page = reader.pages[0]
    text_lines = page.extract_text().split("\n")
    last_updated = extract_last_updated(text_lines)
    debtor_type = extract_debtor_type(text_lines)

    step_text_list = [t for t in text_lines if "devedores" in t.lower()]
    if step_text_list:
        step_text = (
            step_text_list[0]
            .lower()
            .replace("devedores de", "")
            .strip()
            .replace("€", "")
            .replace(".", "")
            .strip()
        )
        if "mais de" in step_text:
            step_start = step_text.split("mais de")[-1].strip()
            step = Step(start=int(step_start))
        else:
            step_start, step_end = step_text.split(" a ")
            step = Step(start=int(step_start), end=int(step_end))
        return Metadata(
            step=step,
            debtor_type=debtor_type,
            last_updated=last_updated,
        )
    raise NoDataException


def extract_last_updated(text_lines: list[str]) -> str | None:
    for line in text_lines:
        if "actualizada" in line.lower():
            last_updated = line.split("em")[-1].strip()
            return last_updated
    return None


def extract_debtor_type(text_lines: list[str]) -> DebtorType:
    if "singulares" in text_lines[0].lower():
        return DebtorType.SINGULAR
    return DebtorType.COLECTIVE


def parse_singular_debtor(row: pd.Series, step: Step) -> SingularDebtor:
    nif = extract_number(row, "NIF")
    name = extract_string(row, "NOME")

    return SingularDebtor(nif=nif, name=name, step=step)


def parse_colective_debtor(
    row: pd.Series, step: Step
) -> ColectiveDebtor:
    nipc = extract_number(row, "NIPC")
    name = extract_string(row, "DESIGNAÇÃO")

    return ColectiveDebtor(nipc=nipc, name=name, step=step)
