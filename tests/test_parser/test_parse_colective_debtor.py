import pandas as pd
import pytest
from src.models import Step, ColectiveDebtor
from src.parser import parse_colective_debtor


def test_parse_colective_debtor_with_valid_data():
    # Create a pandas Series object with valid data
    row = pd.Series({"NIPC": 123456789, "DESIGNAÇÃO": "Cats & Dogs company"})
    step = Step(start=100, end=200)

    # Call the parse_colective_debtor function
    result = parse_colective_debtor(row, step)

    # Check if the result is an instance of ColectiveDebtor
    assert isinstance(result, ColectiveDebtor)

    # Check if the attributes of the ColectiveDebtor object match the expected values
    assert result.nipc == 123456789
    assert result.name == "Cats & Dogs company"
    assert result.step == step


def test_parse_colective_debtor_with_missing_data():
    # Create a pandas Series object with missing data
    row = pd.Series({"NIPC": pd.NA, "DESIGNAÇÃO": pd.NA})
    step = Step(start=100, end=200)

    # Call the parse_colective_debtor function
    with pytest.raises(ValueError):
        parse_colective_debtor(row, step)
