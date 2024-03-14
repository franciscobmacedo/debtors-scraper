from src.parser import extract_last_updated


def test_extract_last_updated_with_matching_line():
    # Create a list of text lines with a matching line
    text_lines = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "Esta linha foi actualizada em 2022-01-01",
        "Nulla facilisi. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae;",
    ]

    # Call the extract_last_updated function
    result = extract_last_updated(text_lines)

    # Check if the result matches the expected value
    assert result == "2022-01-01"


def test_extract_last_updated_without_matching_line():
    # Create a list of text lines without a matching line
    text_lines = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "Nulla facilisi. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae;",
    ]

    # Call the extract_last_updated function
    result = extract_last_updated(text_lines)

    # Check if the result is None
    assert result is None
