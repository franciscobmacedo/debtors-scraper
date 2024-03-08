# Devedores Scraper

The Portuguese Tax Authority holds a list of all of it's debtors, from singular individuals to colective entities here:

https://static.portaldasfinancas.gov.pt/app/devedores_static/de-devedores.html

This information is presented in a set of PDFs, making it hard to search, analyse or actually find someone in it.

This is a scraper that fetches this data, parses the PDF files, and joins them together in json files. 

Everyday, github actions run the scraper and update the main [json file](./data/debtors.json), that works as a JSON API for the frontend version of this project:

https://debtors.fmacedo.com

The code for the frontend can be found [here](https://github.com/franciscobmacedo/devedores).

The entire platform runs free of charge, using github actions to update the backend service, github to serve the json data and cloudflare pages to host the frontend.

## Installation

1. Clone the repository:

    ```shell
    git clone https://github.com/franciscomacedo/devedores-scraper.git
    ```

2. Install the required dependencies:

    ```shell
    poetry install
    ```

## Usage

1. Navigate to the project directory:

    ```shell
    cd devedores-scraper
    ```

2. Run the `run.py` script:

    ```shell
    python run.py
    ```

    This will execute the `main()` function, which sets up the configuration, fetches data, parses files, and joins them together.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.
