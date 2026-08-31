# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
# ]
# ///
"""
Enriches the debtor companies with public data from their Racius profiles
(racius.com): official name, morada, concelho/distrito, forma jurídica,
capital social, CAE and atividade.

Results are written as shards under data/companies/<first-4-digits>.json so the
frontend can fetch just the shard it needs. Already-enriched NIPCs are skipped,
so the script is resumable and cheap to re-run; missing NIPCs are processed
biggest debt bracket first.

Run with: uv run racius_scraper.py [--limit N]
"""

import argparse
import html
import json
import os
import re
import sys
import time
from datetime import date

import requests

BASE = "https://www.racius.com"
SEARCH_URL = f"{BASE}/empresas-em-portugal/?q={{nipc}}"
SHARDS_DIR = "data/companies"
DELAY = 0.6

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

RESULT_LINK_RE = re.compile(r'href="(/[a-z0-9-]+/)" class="results__col-link"')
NO_RESULTS_RE = re.compile(r"\b0 resultados?\b")
PAIR_RE = re.compile(
    r'detail__key-info">\s*([^<]+?)\s*</p>\s*<p class="t--d-blue">\s*([^<]+?)\s*</p>'
)
H1_RE = re.compile(r"<h1[^>]*>\s*([^<]+)")
CAE_RE = re.compile(r">\s*CAE\s*<.{0,400}?>(\d{4,5})<(.{0,400}?)</li>", re.S)
ATIVIDADE_RE = re.compile(r">\s*Atividade\s*<.{0,300}?>\s*(No âmbito de [^<]+?)\s*<", re.S)

DISTRITOS = {
    "Aveiro", "Beja", "Braga", "Bragança", "Castelo Branco", "Coimbra", "Évora",
    "Faro", "Guarda", "Leiria", "Lisboa", "Portalegre", "Porto", "Santarém",
    "Setúbal", "Viana do Castelo", "Vila Real", "Viseu",
    "Região Autónoma da Madeira", "Região Autónoma dos Açores", "Madeira", "Açores",
}


class Racius:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "pt-PT,pt;q=0.9"})
        self.failures = 0

    def get(self, url: str) -> str | None:
        for attempt in range(4):
            try:
                r = self.s.get(url, timeout=60)
            except requests.RequestException:
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code == 200:
                self.failures = 0
                time.sleep(DELAY)
                return r.text
            if r.status_code == 404:
                time.sleep(DELAY)
                return None
            # 403/429/5xx: back off hard — don't hammer their WAF
            self.failures += 1
            if self.failures >= 10:
                raise RuntimeError(f"Too many consecutive failures (last: HTTP {r.status_code})")
            time.sleep(30 * (attempt + 1))
        return None


def parse_profile(text: str) -> dict:
    out: dict = {}
    flat = re.sub(r"\s+", " ", text)
    if m := H1_RE.search(flat):
        out["nome"] = html.unescape(m.group(1)).strip()
    concelho_distrito = None
    for key, value in PAIR_RE.findall(flat):
        key, value = html.unescape(key).strip(), html.unescape(value).strip()
        if key == "Morada":
            out["morada"] = value
        elif key == "Forma Jurídica":
            out["forma"] = value
        elif key == "Capital Social":
            out["capital"] = value
        elif value in DISTRITOS:
            # the concelho→distrito pair is labeled with the concelho itself
            concelho_distrito = (key, value)
    if concelho_distrito:
        out["concelho"], out["distrito"] = concelho_distrito
    if m := CAE_RE.search(flat):
        out["cae"] = m.group(1)
        # the tail mixes separators ("-") with the description — keep the first
        # text fragment that actually has letters
        for frag in re.findall(r">\s*([^<>]+?)\s*<", m.group(2)):
            frag = html.unescape(frag).strip(" -–")
            if len(frag) >= 3 and re.search(r"[A-Za-zÀ-ÿ]", frag):
                out["cae_desc"] = frag
                break
    if m := ATIVIDADE_RE.search(flat):
        out["atividade"] = html.unescape(m.group(1)).strip()
    return out


def shard_path(nipc: int) -> str:
    return os.path.join(SHARDS_DIR, f"{str(nipc)[:4]}.json")


def load_shards() -> dict[str, dict]:
    shards: dict[str, dict] = {}
    if not os.path.isdir(SHARDS_DIR):
        return shards
    for fn in os.listdir(SHARDS_DIR):
        if fn.endswith(".json"):
            with open(os.path.join(SHARDS_DIR, fn)) as f:
                shards[fn[:-5]] = json.load(f)
    return shards


def save_shard(prefix: str, data: dict):
    os.makedirs(SHARDS_DIR, exist_ok=True)
    tmp = os.path.join(SHARDS_DIR, f".{prefix}.tmp")
    with open(tmp, "w") as f:
        json.dump(dict(sorted(data.items())), f, indent=1, ensure_ascii=False)
    os.replace(tmp, os.path.join(SHARDS_DIR, f"{prefix}.json"))


def company_universe() -> list[tuple[int, int]]:
    """All empresa NIPCs across both lists, with their max debt-bracket start."""
    best: dict[int, int] = {}
    for path in ("data/debtors.json", "data/ss-debtors.json"):
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = json.load(f)
        for d in data.get("colective_debtors", []):
            nipc = d["nipc"]
            best[nipc] = max(best.get(nipc, 0), d["step"]["start"])
    return sorted(best.items(), key=lambda t: -t[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max companies to fetch this run")
    args = ap.parse_args()

    shards = load_shards()
    done = {int(n) for shard in shards.values() for n in shard}
    universe = company_universe()
    todo = [(n, s) for n, s in universe if n not in done]
    print(f"{len(universe)} companies, {len(done)} enriched, {len(todo)} to go")
    if args.limit:
        todo = todo[: args.limit]

    racius = Racius()
    today = date.today().isoformat()
    processed = 0
    dirty: set[str] = set()

    def flush():
        for prefix in dirty:
            save_shard(prefix, shards[prefix])
        dirty.clear()

    try:
        for nipc, _ in todo:
            prefix = str(nipc)[:4]
            shard = shards.setdefault(prefix, {})
            search = racius.get(SEARCH_URL.format(nipc=nipc))
            entry: dict = {"checked": today}
            if search and (m := RESULT_LINK_RE.search(search)):
                slug = m.group(1)
                entry["slug"] = slug.strip("/")
                profile = racius.get(BASE + slug)
                if profile:
                    entry.update(parse_profile(profile))
            shard[str(nipc)] = entry
            dirty.add(prefix)
            processed += 1
            if processed % 100 == 0:
                flush()
                print(f"  {processed}/{len(todo)} (last: {nipc} {'ok' if 'slug' in entry else 'not found'})")
    finally:
        flush()
    print(f"Done: {processed} companies enriched this run")


if __name__ == "__main__":
    sys.exit(main())
