"""Ingest the four REAL pitch decks and run the full pipeline on each.
Backend API must be running on :8000.

    cd backend && uv run python seeds/seed_real.py
"""

import time
from pathlib import Path

import httpx

API = "http://localhost:8000/api"
DECKS = Path(__file__).parent / "decks"

REAL = [
    ("AirBed&Breakfast", "Brian Chesky", "real_airbnb_2008.md",
     "Book rooms with locals, rather than hotels (2008)"),
    ("Buffer", "Joel Gascoigne", "real_buffer_2011.md",
     "A smarter way to share on social media (2011)"),
    ("Coinbase", "Brian Armstrong", "real_coinbase_2012.md",
     "The easiest way to buy and use bitcoin (2012)"),
    ("UberCab", "Garrett Camp", "real_ubercab_2008.md",
     "Next-generation car service (2008)"),
]

REAL_FOUNDER_HANDLES = ["rauchg", "kiwicopple", "mitchellh"]


def main():
    with httpx.Client(timeout=900) as client:
        for handle in REAL_FOUNDER_HANDLES:
            t0 = time.time()
            r = client.post(f"{API}/outbound/scan", json={"github_handle": handle})
            r.raise_for_status()
            body = r.json()
            cs = body["cold_start"]
            print(f"[scan] @{handle}: {body['founder_name']} score={cs['aggregate']} "
                  f"[{cs['confidence']['low']}-{cs['confidence']['high']}] "
                  f"({time.time() - t0:.0f}s)")

        for company, founder, deck, one_liner in REAL:
            t0 = time.time()
            with open(DECKS / deck, "rb") as f:
                r = client.post(f"{API}/apply",
                                data={"company_name": company, "founder_name": founder,
                                      "one_liner": one_liner},
                                files={"deck": (deck, f, "text/markdown")})
            r.raise_for_status()
            opp_id = r.json()["opportunity_id"]
            print(f"[apply] {company}: {r.json()['evidence_created']} evidence")
            r = client.post(f"{API}/opportunities/{opp_id}/run")
            r.raise_for_status()
            body = r.json()
            print(f"[run]   {company}: status={body['status']} "
                  f"rec={body.get('recommendation')} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    print("=== BrainVC real-deck seed ===")
    main()
    print("=== done ===")
