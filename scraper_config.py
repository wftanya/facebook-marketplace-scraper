"""Shared crawl configuration for the GUI and the standalone scheduler.

The Streamlit GUI (gui.py) writes the latest form inputs here on every rerun;
worker.py reads this file each cycle so background scrapes always use the most
recent query instead of a value captured by a stale Streamlit script run.
"""

import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).with_name("scraper_state.json")

# Mirrors the widget defaults in gui.py.
DEFAULTS = {
    "city": "Hamilton",
    "radius": 250,
    "query": "Horror VHS",
    "max_price": "9999",
    "max_listings": "100",
    "recent_only": False,
    "blacklist_terms": "",
}


def read_state() -> dict:
    """Return the current config, falling back to DEFAULTS for missing keys."""
    state = dict(DEFAULTS)
    try:
        with open(STATE_FILE) as f:
            state.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return state


def write_state(**values) -> None:
    """Merge values into the state file using an atomic replace.

    The temp-file swap keeps worker.py from ever reading a half-written file.
    """
    state = read_state()
    state.update(values)
    state["updated_at"] = datetime.now().isoformat()

    tmp = STATE_FILE.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(STATE_FILE)
