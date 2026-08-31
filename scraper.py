# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "pdfplumber",
# ]
# ///
"""
Scrapes the Portuguese Tax Authority debtors lists (PDFs) and produces
data/debtors.json — the JSON API consumed by https://debtors.fmacedo.com
and the PowerBI dashboards.

Run with: uv run scraper.py
"""

import io
import json
import re
import sys
from datetime import date

import pdfplumber
import requests

BASE_URL = "https://static.portaldasfinancas.gov.pt/app/devedores_static/{filename}"
OUTPUT_FILE = "data/debtors.json"

ENTRY_RE = re.compile(r"^(\d{9})\s+(.+)$")
STEP_RANGE_RE = re.compile(r"Devedores de\s+([\d.]+)\s+a\s+([\d.]+)")
STEP_OPEN_RE = re.compile(r"Devedores de\s+mais de\s+([\d.]+)")
UPDATED_RE = re.compile(r"actualizada em\s+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)


def fetch_pdf(filename: str) -> bytes | None:
    url = BASE_URL.format(filename=filename)
    response = requests.get(url, timeout=120)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.content


def parse_int(text: str) -> int:
    return int(text.replace(".", ""))


def parse_pdf(content: bytes) -> tuple[list[dict], str | None]:
    """Returns (debtors, last_updated) for one PDF."""
    step = None
    last_updated = None
    debtors: list[dict] = []

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue

                if step is None:
                    if m := STEP_RANGE_RE.search(line):
                        step = {"start": parse_int(m.group(1)), "end": parse_int(m.group(2))}
                    elif m := STEP_OPEN_RE.search(line):
                        step = {"start": parse_int(m.group(1)), "end": None}
                if last_updated is None and (m := UPDATED_RE.search(line)):
                    last_updated = m.group(1)

                if m := ENTRY_RE.match(line):
                    debtors.append({"number": int(m.group(1)), "name": m.group(2).strip()})
                elif (
                    debtors
                    and line
                    and not line.startswith(("Contribuintes", "Devedores", "Informação", "NIF ", "NIPC "))
                    and line not in ("NIF NOME", "NIPC DESIGNAÇÃO")
                ):
                    # continuation of a wrapped name from the previous line
                    debtors[-1]["name"] += " " + line

    if step is None:
        raise ValueError("Could not find the debt step (escalão) in the PDF")
    for d in debtors:
        d["step"] = step
    return debtors, last_updated


def scrape_lists(prefix: str, id_key: str) -> tuple[list[dict], list[str]]:
    """Fetches listaF{S,C}1.pdf, 2, ... until a 404. Returns (debtors, update dates)."""
    all_debtors: list[dict] = []
    dates: list[str] = []
    n = 1
    while True:
        filename = f"{prefix}{n}.pdf"
        content = fetch_pdf(filename)
        if content is None:
            break
        debtors, last_updated = parse_pdf(content)
        print(f"  {filename}: {len(debtors)} debtors (updated {last_updated})")
        for d in debtors:
            d[id_key] = d.pop("number")
        all_debtors.extend(debtors)
        if last_updated:
            dates.append(last_updated)
        n += 1
    if not all_debtors:
        raise RuntimeError(f"No data scraped for {prefix}* — did the source format change?")
    return all_debtors, dates


def main():
    print("Scraping singular debtors...")
    singular, dates_s = scrape_lists("listaFS", "nif")
    print("Scraping colective debtors...")
    colective, dates_c = scrape_lists("listaFC", "nipc")

    all_dates = dates_s + dates_c
    last_updated = min(all_dates) if all_dates else date.today().isoformat()

    data = {
        "singular_debtors": [
            {"name": d["name"], "step": d["step"], "nif": d["nif"]} for d in singular
        ],
        "colective_debtors": [
            {"name": d["name"], "step": d["step"], "nipc": d["nipc"]} for d in colective
        ],
        "last_updated": last_updated,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {OUTPUT_FILE}: {len(singular)} singular + {len(colective)} colective, last_updated={last_updated}")


if __name__ == "__main__":
    sys.exit(main())
