# Standalone scrape scheduler.
#
# Replaces the old `while True` / `schedule` loop that lived at the bottom of
# gui.py. Running the loop inside the Streamlit script meant the script never
# finished, so every reconnect spawned another stuck ScriptRunner thread and
# stale threads kept crawling old queries. This process is the single owner of
# the recurring crawl: it reads the latest inputs from scraper_state.json and
# calls the FastAPI backend (app.py), which handles hot-item detection and email.
#
# Usage: python worker.py   (start app.py first)

import random
import sys
import time
from datetime import datetime, time as dtime

import requests

from scraper_config import read_state

BACKEND_URL = "http://127.0.0.1:8000/crawl_facebook_marketplace"

# Pause overnight: skip crawls before this time (matches the old maybe_crawl).
RESUME_AFTER = dtime(6, 0)

# Minutes between crawls, re-randomised each cycle to look less bot-like.
MIN_INTERVAL_MIN = 5
MAX_INTERVAL_MIN = 8

# Generous timeout: the backend crawls recent + suggested per comma-separated
# query, each up to ~2 minutes, plus page loads.
REQUEST_TIMEOUT_S = 900


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def build_params(state: dict) -> dict:
    max_price = state["max_price"].replace(",", "").replace("$", "").strip() or "0"
    return {
        "city": state["city"],
        "radius": state["radius"],
        "query": state["query"],
        # Backend expects cents, same as gui.py's crawl().
        "max_price": int(max_price) * 100,
        "max_results_per_query": state["max_listings"],
        "recent_only": str(bool(state["recent_only"])).lower(),
        "blacklist_terms": state["blacklist_terms"],
    }


def run_once() -> None:
    now = datetime.now()
    if now.time() <= RESUME_AFTER:
        log(f"Paused until {RESUME_AFTER:%H:%M}; skipping crawl.")
        return

    state = read_state()
    query = state.get("query", "").strip()
    if not query:
        log("No query set in scraper_state.json; skipping crawl.")
        return

    params = build_params(state)
    log(f"Crawling query={query!r} city={params['city']} radius={params['radius']} "
        f"recent_only={params['recent_only']}")
    try:
        resp = requests.get(BACKEND_URL, params=params, timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        results = resp.json()
    except requests.RequestException as e:
        log(f"Crawl request failed: {e}")
        return

    if not isinstance(results, list):
        log(f"Unexpected backend response: {results!r}")
        return

    hot = sum(1 for r in results if isinstance(r, dict) and r.get("item_type") == "hot")
    log(f"Done: {len(results)} listings ({hot} hot). Backend handles email alerts.")


def main() -> None:
    log(f"Scrape worker started. Backend: {BACKEND_URL}")
    while True:
        try:
            run_once()
        except Exception as e:  # keep the loop alive through unexpected errors
            log(f"Unexpected error in run_once: {e}")

        wait_min = random.randint(MIN_INTERVAL_MIN, MAX_INTERVAL_MIN)
        log(f"Next crawl in ~{wait_min} min.")
        time.sleep(wait_min * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Worker stopped.")
        sys.exit(0)
