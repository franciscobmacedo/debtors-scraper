# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
# ]
# ///
"""
Scrapes the Segurança Social debtors list (JSF/PrimeFaces app) and produces
data/ss-debtors.json with the same schema as the AT list in data/debtors.json.

The site paginates server-side with an unknown total, so each entity-type ×
escalão combination is paged (50 rows at a time) until a short page arrives.

Run with: uv run ss_scraper.py
"""

import html as htmllib
import json
import re
import sys
import time
from datetime import date

import requests

BASE = "https://www.seg-social.pt"
PAGE_URL = f"{BASE}/ptss/sef/lista-devedores/consulta-lista-devedores"
OUTPUT_FILE = "data/ss-debtors.json"

FORM = "sefFormConsultaListaDevedores"
TABLE = f"{FORM}:sefConsultaListaDevedoresTabela"
TIPO = f"{FORM}:sefConsultaListaDevedoresSelectTipoEntidade"
ESC = f"{FORM}:sefConsultaListaDevedoresSelectEscaloes"
NOME = f"{FORM}:sefConsultaListaDevedoresInputNome"
NIF = f"{FORM}:sefConsultaListaDevedoresInputNIF"
CARREGAMENTO_FORM = "sefFormConsultaListaDevedoresCarregamento"
CARREGAR = f"{CARREGAMENTO_FORM}:sefConsultaListaDevedoresRemoteCarregar"

PAGE_SIZE = 50
DELAY = 0.4  # politeness between requests

# escalão code -> (start, end); singulares and coletivas use the same codes,
# the actual ranges are read from the page per entity type.
ROW_RE = re.compile(r"<td[^>]*>(?:<[^>]+>)*([^<]*)(?:</[^>]+>)*</td>", re.S)
VIEWSTATE_RE = re.compile(r'name="javax\.faces\.ViewState" (?:id="[^"]*" )?value="([^"]+)"')
VIEWSTATE_XML_RE = re.compile(r'id="[^"]*javax\.faces\.ViewState[^"]*"><!\[CDATA\[([^\]]+)\]\]>')
UPDATED_RE = re.compile(r"Lista atualizada em:?\s*(\d{4}-\d{2}-\d{2})")
ESC_OPTION_RE = re.compile(r'<option value="([a-z])"[^>]*>([^<]+)</option>')


class Session:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
            }
        )
        self.viewstate = ""
        self.dswid = ""
        self.ctkn = ""
        self.lsu = "/home"

    def url(self):
        return f"{PAGE_URL}?dswid={self.dswid}" if self.dswid else PAGE_URL

    def start(self):
        r = self.s.get(PAGE_URL, timeout=60)
        r.raise_for_status()
        m = re.search(r"dswid=(-?\d+)", r.url) or re.search(r"dswid=(-?\d+)", r.text)
        self.dswid = m.group(1) if m else ""
        vs = VIEWSTATE_RE.search(r.text)
        if not vs:
            raise RuntimeError("No ViewState on initial page — did the site change?")
        self.viewstate = vs.group(1)
        # OWASP CSRFGuard: every POST must echo the page's dynamic token.
        tok = re.search(r"token_value = '([^']+)'", r.text)
        if not tok:
            raise RuntimeError("No CSRF token on initial page — did the site change?")
        self.ctkn = tok.group(1)
        lsu = re.search(r"last_successful_url = '([^']+)'", r.text)
        if lsu:
            self.lsu = lsu.group(1)
        # The page fires a "carregar" remote command on load to initialise the view.
        self.post(
            {
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": CARREGAR,
                "javax.faces.partial.execute": "@all",
                "javax.faces.partial.render": FORM,
                CARREGAR: CARREGAR,
                CARREGAMENTO_FORM: CARREGAMENTO_FORM,
            }
        )

    def post(self, params: dict) -> str:
        data = {
            **params,
            "javax.faces.ViewState": self.viewstate,
            "CTKN_DYN": self.ctkn,
            "x-lsu": self.lsu,
            "x-lbu": f"/ptss/sef/lista-devedores/consulta-lista-devedores?dswid={self.dswid}",
        }
        r = self.s.post(
            self.url(),
            data=data,
            headers={"Faces-Request": "partial/ajax", "X-Requested-With": "XMLHttpRequest"},
            timeout=60,
        )
        r.raise_for_status()
        text = r.text
        if "<error>" in text:
            raise RuntimeError(f"JSF error response: {text[:300]}")
        vs = VIEWSTATE_XML_RE.search(text)
        if vs:
            self.viewstate = vs.group(1)
        time.sleep(DELAY)
        return text

    def form_state(self, tipo: str, escalao: str) -> dict:
        return {
            FORM: FORM,
            f"{TIPO}_input": tipo,
            f"{TIPO}_focus": "",
            f"{ESC}_input": escalao,
            f"{ESC}_focus": "",
            NOME: "",
            NIF: "",
        }

    def select(self, source: str, render: str, tipo: str, escalao: str) -> str:
        return self.post(
            {
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": source,
                "javax.faces.partial.execute": source,
                "javax.faces.partial.render": render,
                "javax.faces.behavior.event": "valueChange",
                "javax.faces.partial.event": "change",
                **self.form_state(tipo, escalao),
            }
        )

    def page(self, tipo: str, escalao: str, first: int) -> str:
        return self.post(
            {
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": TABLE,
                "javax.faces.partial.execute": TABLE,
                "javax.faces.partial.render": TABLE,
                TABLE: TABLE,
                f"{TABLE}_pagination": "true",
                f"{TABLE}_first": str(first),
                f"{TABLE}_rows": str(PAGE_SIZE),
                f"{TABLE}_skipChildren": "true",
                f"{TABLE}_encodeFeature": "true",
                **self.form_state(tipo, escalao),
            }
        )


def parse_rows(xml: str) -> list[tuple[str, int]]:
    """Extracts (name, nif) pairs from a partial-response table update."""
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", xml, re.S):
        cells = [htmllib.unescape(c).strip() for c in ROW_RE.findall(tr)]
        cells = [c for c in cells if c]
        if len(cells) >= 2 and re.fullmatch(r"\d{9}", cells[-1]):
            rows.append((" ".join(cells[:-1]).strip(), int(cells[-1])))
    return rows


def parse_escaloes(xml: str) -> dict[str, dict]:
    """Reads the escalão options for the current entity type, e.g. '7500 a 25000'."""
    out = {}
    for code, label in ESC_OPTION_RE.findall(xml):
        label = htmllib.unescape(label).replace(".", "").replace("\xa0", " ").strip()
        nums = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:,\d+)?", label)]
        if ">=" in label and nums:
            out[code] = {"start": int(nums[0]), "end": None}
        elif len(nums) >= 2:
            out[code] = {"start": int(nums[0]), "end": int(nums[1])}
    return out


def scrape_type(ses: Session, tipo: str) -> tuple[list[dict], dict[str, dict], str | None]:
    label = "coletivas" if tipo == "1" else "singulares"
    xml = ses.select(TIPO, f"{FORM}:sefConsultaListaDevedoresSelectEscaloes {TABLE}", tipo, "a")
    escaloes = parse_escaloes(xml)
    if not escaloes:
        raise RuntimeError(f"No escalões parsed for {label} — did the site change?")
    updated = None
    m = UPDATED_RE.search(xml)
    if m:
        updated = m.group(1)

    debtors: list[dict] = []
    for code, step in sorted(escaloes.items()):
        xml = ses.select(ESC, TABLE, tipo, code)
        m = UPDATED_RE.search(xml)
        if m:
            updated = m.group(1)
        seen: set[int] = set()
        first = 0
        stale = 0
        while True:
            page_xml = ses.page(tipo, code, first)
            rows = parse_rows(page_xml)
            new = [(n, nif) for n, nif in rows if nif not in seen]
            if not new:
                # The server occasionally resets to page 0 (e.g. right after the
                # page size changes) — retry the same offset once before giving up.
                stale += 1
                if not rows or stale >= 2:
                    break
                continue
            stale = 0
            for name, nif in new:
                seen.add(nif)
                debtors.append({"name": name, "nif": nif, "step": step})
            if len(rows) < PAGE_SIZE:
                break
            first += PAGE_SIZE
        print(f"  {label} escalão {code} ({step['start']}-{step['end']}): {len(seen)} debtors")
    return debtors, escaloes, updated


def main():
    ses = Session()
    ses.start()
    print("Scraping Segurança Social debtors...")
    singular, _, updated_s = scrape_type(ses, "2")
    colective, _, updated_c = scrape_type(ses, "1")

    if not singular and not colective:
        raise RuntimeError("No data scraped — did the site change?")

    data = {
        "singular_debtors": [
            {"name": d["name"], "step": d["step"], "nif": d["nif"]} for d in singular
        ],
        "colective_debtors": [
            {"name": d["name"], "step": d["step"], "nipc": d["nif"]} for d in colective
        ],
        "last_updated": updated_s or updated_c or date.today().isoformat(),
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(
        f"Wrote {OUTPUT_FILE}: {len(singular)} singular + {len(colective)} colective, "
        f"last_updated={data['last_updated']}"
    )


if __name__ == "__main__":
    sys.exit(main())
