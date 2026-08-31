#!/bin/bash
# One-time Racius backfill: enrich all debtor companies in resumable batches,
# pushing shard progress after each. Skips pushing around the daily scrape
# workflow (05:00-06:30 UTC) to avoid racing its commit.
set -u
cd "$(dirname "$0")"

email() {
  KEY=$(security find-generic-password -s resend-tlim -a claude -w)
  curl -s -X POST https://api.resend.com/emails \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
    -d "{\"from\":\"Claude <claude@tlim.fmacedo.com>\",\"to\":[\"franciscovcbm@gmail.com\"],\"subject\":\"$1\",\"text\":\"$2\"}" > /dev/null
}

while true; do
  if ! out=$(uv run racius_scraper.py --limit 6000 --workers 8 --rps 8 2>&1); then
    echo "$(date -Is) SCRAPER FAILED: $(echo "$out" | tail -3)"
    email "Racius backfill FAILED" "The Racius backfill on the Mac stopped with an error: $(echo "$out" | tail -1 | tr -d '\"'). Progress so far is committed; rerun backfill_racius.sh in debtors-scraper to resume."
    exit 1
  fi
  echo "$(date -Is) $(echo "$out" | head -1) | $(echo "$out" | tail -1)"

  hour=$(date -u +%H)
  if [ "$hour" != "05" ] && [ "$hour" != "06" ]; then
    git pull --rebase -q origin main || true
    git add data/companies
    git commit -q -m "racius backfill progress" || true
    git push -q origin main || true
  fi

  if echo "$out" | grep -q ", 0 to go"; then
    touch data/companies/.backfill-done
    git add data/companies/.backfill-done
    git commit -q -m "racius backfill complete"
    git push -q origin main
    echo "$(date -Is) BACKFILL COMPLETE"
    break
  fi
done
