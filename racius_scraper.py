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
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
# the search page's Estado facet leaks the activity state that the profile
# page keeps behind the paywall; with exactly 1 result it is this company's
ESTADO_RE = re.compile(r"Estado</legend>.{0,400}?f--700\">([^<]+)</a>\s*<span>\(1\)</span>", re.S)
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
    """Thread-safe client with a global request-rate limiter.

    Requests from all workers are spaced at least `1/rps` apart; any 403/429/5xx
    pushes the whole pool back 30s so we slow down instead of getting banned.
    """

    def __init__(self, rps: float = 1.5):
        self.min_interval = 1.0 / rps
        self._lock = threading.Lock()
        self._next = 0.0
        self._local = threading.local()
        self.failures = 0

    def _session(self) -> requests.Session:
        if not hasattr(self._local, "s"):
            s = requests.Session()
            s.headers.update({"User-Agent": UA, "Accept-Language": "pt-PT,pt;q=0.9"})
            self._local.s = s
        return self._local.s

    def _wait_slot(self, penalty: float = 0.0):
        with self._lock:
            now = time.monotonic()
            slot = max(self._next, now) + penalty
            self._next = slot + self.min_interval
        time.sleep(max(0.0, slot - time.monotonic()))

    def get(self, url: str) -> str | None:
        for attempt in range(4):
            self._wait_slot()
            try:
                r = self._session().get(url, timeout=60)
            except requests.RequestException:
                continue
            if r.status_code == 200:
                with self._lock:
                    self.failures = 0
                return r.text
            if r.status_code == 404:
                return None
            # 403/429/5xx: push the whole pool back — don't hammer their WAF
            with self._lock:
                self.failures += 1
                if self.failures >= 20:
                    raise RuntimeError(
                        f"Too many consecutive failures (last: HTTP {r.status_code})"
                    )
            self._wait_slot(penalty=30.0 * (attempt + 1))
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
    ap.add_argument("--nipc", help="comma-separated NIPCs to (re)fetch, ignoring the done-set")
    ap.add_argument("--workers", type=int, default=1, help="concurrent fetchers")
    ap.add_argument("--rps", type=float, default=1.5, help="max requests per second (global)")
    args = ap.parse_args()

    shards = load_shards()
    if args.nipc:
        todo = [(int(n.strip()), 0) for n in args.nipc.split(",")]
        print(f"targeted run: {len(todo)} companies")
    else:
        done = {int(n) for shard in shards.values() for n in shard}
        universe = company_universe()
        todo = [(n, s) for n, s in universe if n not in done]
        print(f"{len(universe)} companies, {len(done)} enriched, {len(todo)} to go")
        if args.limit:
            todo = todo[: args.limit]

    racius = Racius(rps=args.rps)
    today = date.today().isoformat()
    processed = 0
    started = time.monotonic()
    state_lock = threading.Lock()
    dirty: set[str] = set()

    def flush():
        with state_lock:
            pending = list(dirty)
            dirty.clear()
        for prefix in pending:
            save_shard(prefix, shards[prefix])

    def fetch(nipc: int) -> dict:
        entry: dict = {"checked": today}
        search = racius.get(SEARCH_URL.format(nipc=nipc))
        if search and (m := RESULT_LINK_RE.search(search)):
            slug = m.group(1)
            entry["slug"] = slug.strip("/")
            if em := ESTADO_RE.search(re.sub(r"\s+", " ", search)):
                estado = html.unescape(em.group(1)).strip()
                entry["estado"] = {"Encerradas": "Encerrada"}.get(estado, estado)
            profile = racius.get(BASE + slug)
            if profile:
                entry.update(parse_profile(profile))
        return entry

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(fetch, nipc): nipc for nipc, _ in todo}
            for fut in as_completed(futures):
                nipc = futures[fut]
                entry = fut.result()  # propagate hard failures and stop the run
                prefix = str(nipc)[:4]
                with state_lock:
                    shards.setdefault(prefix, {})[str(nipc)] = entry
                    dirty.add(prefix)
                    processed += 1
                    count = processed
                if count % 200 == 0:
                    flush()
                    rate = count / (time.monotonic() - started)
                    print(f"  {count}/{len(todo)} ({rate:.1f}/s)", flush=True)
    finally:
        flush()
    print(f"Done: {processed} companies enriched this run")


if __name__ == "__main__":
    sys.exit(main())
