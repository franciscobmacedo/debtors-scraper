from src.parser import parse_file
from src.models import DebtorType, SingularDebtor, ColectiveDebtor, Metadata, Step
from src.exceptions import NoDataException
import pytest
from tests.fixtures.pdf_generator import generate_test_pdf


def test_parse_file_with_singular_debtors(mocker, tmp_path):
    mocker.patch(
        "src.parser.extract_metadata",
        return_value=Metadata(
            debtor_type=DebtorType.SINGULAR,
            step=Step(start=7500, end=25000),
            last_updated="2024-03-13",
        ),
    )

    content = generate_test_pdf(
        [
            "Contribuintes Singulares",
            "Devedores de 7.500 a 25.000 €",
            "Informação actualizada em 2024-03-13",
        ],
        table_data=[
            ["NIF", "NOME"],
            [123456789, "JOHN SMITH"],
            [222222222, "SARAH MARSHALL"],
        ],
    )
    filepath = tmp_path / "test.pdf"
    filepath.write_bytes(content)
    # filepath = "tests/fixtures/files/singular_debtor_sample.pdf"
    debtors, _ = parse_file(filepath)
    assert len(debtors) == 2
    assert isinstance(debtors[0], SingularDebtor)
    assert isinstance(debtors[1], SingularDebtor)
    assert debtors[0].name == "JOHN SMITH"
    assert debtors[0].nif == 123456789
    assert debtors[1].name == "SARAH MARSHALL"
    assert debtors[1].nif == 222222222


def test_parse_file_with_colective_debtors(mocker, tmp_path):
    mocker.patch(
        "src.parser.extract_metadata",
        return_value=Metadata(
            debtor_type=DebtorType.COLECTIVE,
            step=Step(start=10000, end=50000),
            last_updated="2024-03-13",
        ),
    )

    content = generate_test_pdf(
        [
            "Contribuintes Colecivos",
            "Devedores de 10.000 a 50.000 €",
            "Informação actualizada em 2024-03-13",
        ],
        table_data=[
            ["NIPC", "DESIGNAÇÃO"],
            [509123456, "Cats & Dogs company "],
            [509222222, "Food and Drinks company"],
        ],
    )

    filepath = tmp_path / "test.pdf"
    filepath.write_bytes(content)

    debtors, _ = parse_file(filepath)
    assert len(debtors) == 2
    assert isinstance(debtors[0], ColectiveDebtor)
    assert isinstance(debtors[1], ColectiveDebtor)
    assert debtors[0].name == "Cats & Dogs company"
    assert debtors[0].nipc == 509123456
    assert debtors[1].name == "Food and Drinks company"
    assert debtors[1].nipc == 509222222


def test_parse_file_with_no_data(mocker, tmp_path):
    mocker.patch(
        "src.parser.extract_metadata",
        return_value=Metadata(
            debtor_type=DebtorType.COLECTIVE,
            step=Step(start=10000, end=50000),
            last_updated="2024-03-13",
        ),
    )

    content = generate_test_pdf(
        [
            "Contribuintes Colecivos",
            "Devedores de 10.000 a 50.000 €",
            "Informação actualizada em 2024-03-13",
        ],
    )

    filepath = tmp_path / "test.pdf"
    filepath.write_bytes(content)

    with pytest.raises(NoDataException):
        parse_file(filepath)
