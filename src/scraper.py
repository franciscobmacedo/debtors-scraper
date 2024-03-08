import os

import requests
from src.config import BASE_URL, JSON_FILES_PATH, RAW_FILES_PATH


def setup():
    os.makedirs(RAW_FILES_PATH, exist_ok=True)
    os.makedirs(JSON_FILES_PATH, exist_ok=True)


def dump_file(filename, content: str):
    filepath = os.path.join(RAW_FILES_PATH, filename)
    with open(filepath, "wb") as f:
        f.write(content)

def fetch_file_data(base_filename: str):
    count = 1
    while True:
        filename = base_filename.format(n=count)
        url = BASE_URL.format(filename=filename)
        response = requests.get(url)
        if response.status_code == 404:
            break
        dump_file(filename, response.content)
        count += 1


def fetch_data():
    fetch_file_data("listaFS{n}.pdf")
    fetch_file_data("listaFC{n}.pdf")
