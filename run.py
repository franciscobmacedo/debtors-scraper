from src.config import setup
from src.scraper import fetch_data
from src.parser import parse_files
from src.joiner import join_files


def main():
    setup()
    fetch_data()
    parse_files()
    join_files()


if __name__ == "__main__":
    main()
