from src.config import BASE_URL, JSON_FILES_PATH, MAIN_FILE_NAME, RAW_FILES_PATH, setup
from src.joiner import join_files
from src.parser import parse_files
from src.scraper import Scraper


def main():
    setup()
    Scraper(BASE_URL, RAW_FILES_PATH).fetch_data()
    parse_files(RAW_FILES_PATH, JSON_FILES_PATH)
    join_files(JSON_FILES_PATH, MAIN_FILE_NAME)


if __name__ == "__main__":
    main()
