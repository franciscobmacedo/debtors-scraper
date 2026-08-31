# Debtors Scraper

The Portuguese Tax Authority (AT) publishes its list of debtors — from individuals to companies — as a set of PDFs:

https://static.portaldasfinancas.gov.pt/app/devedores_static/de-devedores.html

That format makes it hard to search or analyse. This scraper fetches the PDFs, parses them, and publishes a single JSON file that works as a read-only API:

```
https://raw.githubusercontent.com/franciscobmacedo/debtors-scraper/main/data/debtors.json
```

It powers the frontend at https://debtors.fmacedo.com ([code](https://github.com/franciscobmacedo/debtors)) and the PowerBI dashboards embedded there. **The path `data/debtors.json` and its schema are a stable contract — don't move or rename it.**

## Schema

```json
{
  "singular_debtors": [{ "name": "...", "nif": 123456789, "step": { "start": 7500, "end": 25000 } }],
  "colective_debtors": [{ "name": "...", "nipc": 500000000, "step": { "start": 1000000, "end": null } }],
  "last_updated": "2026-08-30"
}
```

`step` is the debt bracket (escalão); `end: null` means open-ended ("mais de X €").

## Running

Requires [uv](https://docs.astral.sh/uv/) — dependencies are declared inline in the script:

```shell
uv run scraper.py
```

## Updates

A daily cron job runs the scraper and commits the refreshed `data/debtors.json` to this repository.
