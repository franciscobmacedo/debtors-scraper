import json
from src.exceptions import NoDataException
from src.joiner import join_files
import pytest


def test_join_files(tmp_path):
    tmp_directory = tmp_path / "files"
    tmp_directory.mkdir()
    singular_debtors_file = tmp_directory / "listaFS1.json"
    singular_debtors_data = {
        "last_updated": "2022-01-01",
        "debtors": [
            {
                "name": "John",
                "step": {"start": 7500, "end": 25000},
                "nif": 123456789,
            },
            {
                "name": "Sarah",
                "step": {"start": 7500, "end": 25000},
                "nif": 222222222,
            },
        ],
    }

    colective_debtors_file = tmp_directory / "listaFC1.json"
    colective_debtors_data = {
        "last_updated": "2022-01-02",
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
    }
    with open(singular_debtors_file, "w") as f:
        json.dump(singular_debtors_data, f)

    with open(colective_debtors_file, "w") as f:
        json.dump(colective_debtors_data, f)

    # Call the function under test
    join_files(tmp_directory, "main.json")

    with open(tmp_directory / "main.json") as f:
        result = json.load(f)
        assert result["last_updated"] == "2022-01-01"
        assert result["singular_debtors"] == singular_debtors_data["debtors"]
        assert result["colective_debtors"] == colective_debtors_data["debtors"]


def test_join_files_fail_with_wrong_keys(tmp_path):
    """Test that join_files raises a ValueError if the structure of the files is not correct"""
    tmp_directory = tmp_path / "files"
    tmp_directory.mkdir()
    singular_debtors_file = tmp_directory / "listaFS1.json"
    singular_debtors_data = {
        "last_updated": "2022-01-01",
        "debtors": [
            {
                "name": "John",
                "wrong_key": {"start": 7500, "end": 25000},
                "nif": 123456789,
            },
            {
                "name": "Sarah",
                "wrong_key": {"start": 7500, "end": 25000},
                "nif": 222222222,
            },
        ],
    }

    with open(singular_debtors_file, "w") as f:
        json.dump(singular_debtors_data, f)

    with pytest.raises(ValueError):
        join_files(tmp_directory, "main.json")


def test_joiner_skips_files_with_wrong_name_format(tmp_path):
    """Test that join_files skips files with wrong name format and raises a NoDataException if None of the files are correct."""
    tmp_directory = tmp_path / "files"
    tmp_directory.mkdir()
    wrong_file_name = tmp_directory / "wrong_file_name.json"
    wrong_file_data = "some fake data"

    with open(wrong_file_name, "w") as f:
        json.dump(wrong_file_data, f)

    # Assert that the function under test raises a NoDataException
    with pytest.raises(NoDataException):
        join_files(tmp_directory, "main.json")


def test_joiner_with_only_singular_debtors_works(tmp_path):
    tmp_directory = tmp_path / "files"
    tmp_directory.mkdir()
    singular_debtors_file = tmp_directory / "listaFS1.json"
    singular_debtors_data = {
        "last_updated": "2022-01-01",
        "debtors": [
            {
                "name": "John",
                "step": {"start": 7500, "end": 25000},
                "nif": 123456789,
            },
            {
                "name": "Sarah",
                "step": {"start": 7500, "end": 25000},
                "nif": 222222222,
            },
        ],
    }

    with open(singular_debtors_file, "w") as f:
        json.dump(singular_debtors_data, f)

    # Call the function under test
    join_files(tmp_directory, "main.json")

    with open(tmp_directory / "main.json") as f:
        result = json.load(f)
        assert result["last_updated"] == "2022-01-01"
        assert result["singular_debtors"] == singular_debtors_data["debtors"]
        assert result["colective_debtors"] == []


def test_joiner_with_only_colective_debtors_works(tmp_path):
    tmp_directory = tmp_path / "files"
    tmp_directory.mkdir()

    colective_debtors_file = tmp_directory / "listaFC1.json"
    colective_debtors_data = {
        "last_updated": "2022-01-02",
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
    }

    with open(colective_debtors_file, "w") as f:
        json.dump(colective_debtors_data, f)

    # Call the function under test
    join_files(tmp_directory, "main.json")

    with open(tmp_directory / "main.json") as f:
        result = json.load(f)
        assert result["last_updated"] == "2022-01-02"
        assert result["singular_debtors"] == []
        assert result["colective_debtors"] == colective_debtors_data["debtors"]
