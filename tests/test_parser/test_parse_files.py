import json

from src.exceptions import NoDataException
from src.models import (
    ColectiveDebtor,
    DebtorType,
    Metadata,
    SingularDebtor,
    Step,
)
from src.parser import parse_files


def test_parse_files_with_singular_debtors(mocker, tmp_path):
    # Create a temporary source directory
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Create a temporary destination directory
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    # Create a temporary source file
    source_file = source_dir / "singular.pdf"
    source_file.write_bytes(b"")

    # Create a temporary destination file
    dest_file = dest_dir / "singular.json"

    mocker.patch(
        "src.parser.parse_file",
        return_value=(
            [
                SingularDebtor(
                    nif=123456789, name="JOHN SMITH", step=Step(start=7500, end=25000)
                ),
                SingularDebtor(
                    nif=222222222,
                    name="SARAH MARSHALL",
                    step=Step(start=7500, end=25000),
                ),
            ],
            Metadata(
                debtor_type=DebtorType.SINGULAR,
                step=Step(start=7500, end=25000),
                last_updated="2024-03-13",
            ),
        ),
    )

    # Call the parse_files function
    parse_files(str(source_dir), str(dest_dir))

    # Check if the destination file exists
    assert dest_file.exists()

    # Read the contents of the destination file
    with open(str(dest_file), "r") as f:
        file_contents = json.load(f)

    assert file_contents == {
        "debtors": [
            {
                "name": "JOHN SMITH",
                "step": {"start": 7500, "end": 25000},
                "nif": 123456789,
            },
            {
                "name": "SARAH MARSHALL",
                "step": {"start": 7500, "end": 25000},
                "nif": 222222222,
            },
        ],
        "last_updated": "2024-03-13",
    }


def test_parse_files_with_colective_debtors(mocker, tmp_path):
    # Create a temporary source directory
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Create a temporary destination directory
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    # Create a temporary source file
    source_file = source_dir / "colective.pdf"
    source_file.write_bytes(b"")

    # Create a temporary destination file
    dest_file = dest_dir / "colective.json"

    mocker.patch(
        "src.parser.parse_file",
        return_value=(
            [
                ColectiveDebtor(
                    nipc=509123456,
                    name="Cats & Dogs company",
                    step=Step(start=10000, end=50000),
                ),
                ColectiveDebtor(
                    nipc=509222222,
                    name="Food and Drinks company",
                    step=Step(start=10000, end=50000),
                ),
            ],
            Metadata(
                debtor_type=DebtorType.COLECTIVE,
                step=Step(start=10000, end=50000),
                last_updated="2024-03-13",
            ),
        ),
    )

    # Call the parse_files function
    parse_files(str(source_dir), str(dest_dir))

    # Check if the destination file exists
    assert dest_file.exists()

    # Read the contents of the destination file
    with open(str(dest_file), "r") as f:
        file_contents = json.load(f)

    assert file_contents == {
        "debtors": [
            {
                "name": "Cats & Dogs company",
                "step": {"start": 10000, "end": 50000},
                "nipc": 509123456,
            },
            {
                "name": "Food and Drinks company",
                "step": {"start": 10000, "end": 50000},
                "nipc": 509222222,
            },
        ],
        "last_updated": "2024-03-13",
    }


def test_parse_files_with_no_data(mocker, tmp_path):
    # Create a temporary source directory
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Create a temporary destination directory
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    # Create a temporary source file
    source_file = source_dir / "empty.pdf"
    source_file.write_bytes(b"")

    # Create a temporary destination file
    dest_file = dest_dir / "empty.json"

    mocker.patch("src.parser.parse_file", side_effect=NoDataException)

    # # Call the parse_files function
    parse_files(str(source_dir), str(dest_dir))

    # Check if the destination file does not exist
    assert not dest_file.exists()
