import os

import requests

class Scraper:
    def __init__(self, base_url: str, dest_dir: str):
        self.base_url = base_url
        self.dest_dir = dest_dir
            
    def dump_file(self, filename, content: str):
        filepath = os.path.join(self.dest_dir, filename)
        with open(filepath, "wb") as f:
            f.write(content)

    def fetch_file_data(self, base_filename: str):
        count = 1
        while True:
            filename = base_filename.format(n=count)
            url = self.base_url.format(filename=filename)
            response = requests.get(url)
            if response.status_code == 404:
                break
            self.dump_file(filename, response.content)
            count += 1


    def fetch_data(self):
        self.fetch_file_data("listaFS{n}.pdf")
        self.fetch_file_data("listaFC{n}.pdf")
