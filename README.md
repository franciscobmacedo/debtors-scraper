# Debtors Scraper

Scrapers for Portugal's two public debtors lists, published as JSON:

- **AT / Fisco** (`scraper.py`): the Tax Authority publishes its list as [a set of PDFs](https://static.portaldasfinancas.gov.pt/app/devedores_static/de-devedores.html). Output: `data/debtors.json`.
- **Segurança Social** (`ss_scraper.py`): published only through [a session-bound JSF web app](https://www.seg-social.pt/ptss/sef/lista-devedores/consulta-lista-devedores); the scraper replays its AJAX pagination. Output: `data/ss-debtors.json`.

Both files work as a read-only API:

```
https://raw.githubusercontent.com/franciscobmacedo/debtors-scraper/main/data/debtors.json
https://raw.githubusercontent.com/franciscobmacedo/debtors-scraper/main/data/ss-debtors.json
```

They power the frontend at https://debtors.fmacedo.com ([code](https://github.com/franciscobmacedo/debtors)) and the PowerBI dashboards embedded there. **These paths and their schema are a stable contract — don't move or rename them.**

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
