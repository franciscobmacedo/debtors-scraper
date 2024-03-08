import pandas as pd
import json
import os
from src.utils import (
    extract_number,
    extract_string,
    is_number,
    is_decimal,
    try_int,
    dump_json,
)


def test_extract_number_with_numeric_value():
    # Create a pandas Series object with a numeric value
    row = pd.Series({"key": 123})

    # Call the extract_number function
    result = extract_number(row, "key")

    # Check if the result matches the expected value
    assert result == 123


def test_extract_number_with_string_value():
    # Create a pandas Series object with a string value
    row = pd.Series({"key": "456"})

    # Call the extract_number function
    result = extract_number(row, "key")

    # Check if the result matches the expected value
    assert result == "456"


def test_extract_number_with_nan_value():
    # Create a pandas Series object with a NaN value
    row = pd.Series({"key": pd.NA})

    # Call the extract_number function
    result = extract_number(row, "key")

    # Check if the result matches the expected value
    assert pd.isna(result)


def test_extract_number_with_no_matching_value():
    # Create a pandas Series object with no matching value
    row = pd.Series({"key": "abc"})

    # Call the extract_number function
    result = extract_number(row, "key")

    # Check if the result matches the expected value
    assert result == "abc"


def test_extract_string_with_string_value():
    # Create a pandas Series object with a string value
    row = pd.Series({"key": "abc"})

    # Call the extract_string function
    result = extract_string(row, "key")

    # Check if the result matches the expected value
    assert result == "abc"


def test_extract_string_with_numeric_value():
    # Create a pandas Series object with a numeric value
    row = pd.Series({"key": 123})

    # Call the extract_string function
    result = extract_string(row, "key")

    # Check if the result matches the expected value
    assert result == 123


def test_extract_string_with_nan_value():
    # Create a pandas Series object with a NaN value
    row = pd.Series({"key": pd.NA})

    # Call the extract_string function
    result = extract_string(row, "key")

    # Check if the result matches the expected value
    assert pd.isna(result)


def test_extract_string_with_no_matching_value():
    # Create a pandas Series object with no matching value
    row = pd.Series({"key": 456})

    # Call the extract_string function
    result = extract_string(row, "key")

    # Check if the result matches the expected value
    assert result == 456


def test_is_number():
    # Test with integer input
    assert is_number(10)
    assert is_number(-5)

    # Test with string input
    assert is_number("123")
    assert is_number("-456")

    # Test with decimal input
    assert is_number(3.14)
    assert is_number("-2.5")

    # Test with non-number input
    assert not is_number("abc")
    assert not is_number("1a2b3c")
    assert not is_number("12.34.56")

    # Test with other data types
    assert not is_number(True)
    assert not is_number(None)
    assert not is_number([])


def test_is_decimal():
    # Test cases for valid decimal values
    assert is_decimal("3.14")
    assert is_decimal("-2.5")
    assert is_decimal("0.0")
    assert is_decimal("1234567890.0987654321")
    assert is_decimal(3.14)

    # Test cases for invalid decimal values
    assert not is_decimal("abc")
    assert not is_decimal("1.23.45")
    assert not is_decimal("1,234.56")


def test_try_int_with_valid_integer():
    assert try_int("123") == 123


def test_try_int_with_invalid_integer():
    assert try_int("abc") is None


def test_try_int_with_empty_string():
    assert try_int("") is None


def test_try_int_with_none_value():
    assert try_int(None) is None


def test_dump_json(tmpdir):
    # Create a temporary file path
    file_path = os.path.join(tmpdir, "test.json")

    # Define test data
    data = {"name": "John", "age": 30}

    # Call the function under test
    dump_json(file_path, data)

    # Read the contents of the file
    with open(file_path, "r") as f:
        file_contents = json.load(f)

    # Assert that the file contents match the test data
    assert file_contents == data
