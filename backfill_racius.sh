#!/bin/bash
# One-time Racius backfill: enrich all debtor companies in resumable batches,
# pushing shard progress periodically. Skips pushing around the daily scrape
# workflow (05:00-06:30 UTC) to avoid racing its commit.
set -e
cd "$(dirname "$0")"

while true; do
  out=$(uv run racius_scraper.py --limit 2000 2>&1)
  echo "$(date -Is) $(echo "$out" | head -1) | $(echo "$out" | tail -1)"

  hour=$(date -u +%H)
  if [ "$hour" != "05" ] && [ "$hour" != "06" ]; then
    git pull --rebase -q origin main || true
    git add data/companies
    git commit -q -m "racius backfill progress" || true
    git push -q origin main || true
  fi

  if echo "$out" | grep -q " 0 to go"; then
    touch data/companies/.backfill-done
    git add data/companies/.backfill-done
    git commit -q -m "racius backfill complete"
    git push -q origin main
    echo "$(date -Is) BACKFILL COMPLETE"
    break
  fi
done
