import pandas as pd
import pytest
from src.models import SingularDebtor, Step
from src.parser import parse_singular_debtor


def test_parse_singular_debtor_with_valid_data():
    # Create a pandas Series object with valid data
    row = pd.Series({"NIF": 123456789, "NOME": "John"})
    step = Step(start=100, end=200)

    # Call the parse_colective_debtor function
    result = parse_singular_debtor(row, step)

    # Check if the result is an instance of ColectiveDebtor
    assert isinstance(result, SingularDebtor)

    # Check if the attributes of the ColectiveDebtor object match the expected values
    assert result.nif == 123456789
    assert result.name == "John"
    assert result.step == step


def test_parse_singular_debtor_with_missing_data():
    # Create a pandas Series object with missing data
    row = pd.Series({"NIF": pd.NA, "NOME": pd.NA})
    step = Step(start=100, end=200)

    # Call the parse_colective_debtor function
    with pytest.raises(ValueError):
        parse_singular_debtor(row, step)


def test_parse_singular_debtor_with_wrong_data():
    # Create a pandas Series object with missing data
    row = pd.Series({"NIF": pd.NA, "WRONG_COL": pd.NA})
    step = Step(start=100, end=200)

    # Call the parse_colective_debtor function
    with pytest.raises(KeyError):
        parse_singular_debtor(row, step)
