import os

BASE_URL = "https://static.portaldasfinancas.gov.pt/app/devedores_static/{filename}"

RAW_FILES_PATH = "files"
JSON_FILES_PATH = "data"


def setup():
    os.makedirs(RAW_FILES_PATH, exist_ok=True)
    os.makedirs(JSON_FILES_PATH, exist_ok=True)
