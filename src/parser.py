import io
import os

import warnings
import pypdf
import tabula
from src.exceptions import NoDataException
from src.models import (
    ColectiveDebtor,
    DebtorType,
    SingularDebtor,
    Step,
    Metadata,
    SingularDebtorsData,
    ColectiveDebtorsData,
)
from src.utils import dump_json, extract_number, extract_string

warnings.simplefilter(action="ignore", category=FutureWarning)
import pandas as pd


def parse_files(source_dir: str, dest_dir: str):
    for filename in os.listdir(source_dir):
        source = os.path.join(source_dir, filename)
        dest = os.path.join(dest_dir, filename.replace(".pdf", ".json"))
        try:
            debtors, metadata = parse_file(source)
        except NoDataException:
            continue

        if metadata.debtor_type == DebtorType.SINGULAR:
            data = SingularDebtorsData(
                last_updated=metadata.last_updated,
                debtors=debtors,
            )
        else:
            data = ColectiveDebtorsData(
                last_updated=metadata.last_updated,
                debtors=debtors,
            )

        dump_json(dest, data.model_dump())


def parse_file(
    filepath: str,
) -> tuple[list[SingularDebtor | ColectiveDebtor], Metadata]:
    with open(filepath, "rb") as f:
        content = f.read()

    metadata = extract_metadata(content)
    dfs = tabula.read_pdf(filepath, pages="all")
    if not dfs:
        raise NoDataException(f"No debtos data found in the file {filepath}")
    df = pd.concat(dfs)

    parser = (
        parse_singular_debtor
        if metadata.debtor_type == DebtorType.SINGULAR
        else parse_colective_debtor
    )
    debtors = [parser(row, metadata.step) for _, row in df.iterrows()]
    return debtors, metadata


def extract_metadata(content: bytes) -> Metadata:
    if not os.path.exists("test.txt"):
        with open("test.txt", "wb") as f:
            f.write(content)
    pdf_file = io.BytesIO(content)
    
    reader = pypdf.PdfReader(pdf_file)
    if len(reader.pages) == 0:
        raise NoDataException
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


def parse_colective_debtor(row: pd.Series, step: Step) -> ColectiveDebtor:
    nipc = extract_number(row, "NIPC")
    name = extract_string(row, "DESIGNAÇÃO")

    return ColectiveDebtor(nipc=nipc, name=name, step=step)
