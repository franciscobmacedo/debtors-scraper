import pytest

from src.exceptions import NoDataException
from src.models import Metadata, Step
from src.parser import extract_metadata
from tests.fixtures.pdf_generator import generate_test_pdf


def test_extract_metadata_with_step_range():
    content = generate_test_pdf(
        [
            "Contribuintes Singulares",
            "Devedores de 7.500 a 25.000 €",
            "Informação actualizada em 2024-03-13",
        ]
    )

    metadata = extract_metadata(content)
    assert isinstance(metadata, Metadata)
    assert metadata.step == Step(start=7500, end=25000)
    assert metadata.debtor_type == "singular"
    assert metadata.last_updated == "2024-03-13"


def test_extract_metadata_with_step_start():
    content = generate_test_pdf(
        [
            "Contribuintes Singulares",
            "Devedores de mais de 1.000.000 €",
            "Informação actualizada em 2024-03-13",
        ]
    )
    metadata = extract_metadata(content)
    assert isinstance(metadata, Metadata)
    assert metadata.step == Step(start=1000000)
    assert metadata.debtor_type == "singular"
    assert metadata.last_updated == "2024-03-13"


def test_extract_metadata_no_step():
    content = generate_test_pdf(
        ["Contribuintes Singulares", "Informação actualizada em 2024-03-13"]
    )
    with pytest.raises(NoDataException):
        extract_metadata(content)


def test_extract_metadata_no_data():
    content = generate_test_pdf([])
    with pytest.raises(NoDataException):
        extract_metadata(content)


def test_extract_colective_debtor_type():
    content = generate_test_pdf(
        [
            "Contribuintes Colectivos",
            "Devedores de 7.500 a 25.000 €",
            "Informação actualizada em 2024-03-13",
        ]
    )
    metadata = extract_metadata(content)
    assert metadata.debtor_type == "colectivo"
