import os
import json
import httpx
from sec_api import XbrlApi

# Load SEC API key and build client
API_KEY = os.getenv("SEC_API_KEY")
api     = XbrlApi(api_key=API_KEY)

# Your custom User-Agent for EDGAR requests
UA = {"User-Agent": os.getenv("USER_AGENT")}

def parse_information(cik: str, accn: str) -> dict:
    """
    1) Fetches the EDGAR index.json for the given CIK & accession.
    2) Picks the first .htm file in the manifest.
    3) Builds the full htm_url.
    4) Calls sec-api.xbrl_to_json(htm_url=...) and returns the JSON as a dict.
    """
    # Normalize
    no_dash = accn.replace("-", "")
    base    = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{no_dash}"
    idx_url = f"{base}/index.json"

    # 1) Fetch manifest
    r = httpx.get(idx_url, headers=UA, timeout=30)
    r.raise_for_status()
    manifest = r.json()["directory"]["item"]

    # 2) Find first .htm
    htm_fn = next(
        entry["name"]
        for entry in manifest
        if entry["name"].lower().endswith(".htm")
    )

    # 3) Build URL
    htm_url = f"{base}/{htm_fn}"

    # 4) Convert via sec-api
    raw = api.xbrl_to_json(htm_url=htm_url)
    return json.loads(raw) if isinstance(raw, str) else raw


def extract_tags(cik: str, accn: str, tags: list[str]) -> dict[str, float | None]:
    """
    Given a raw sec-api JSON (from parse_information), finds the first 'value'
    for each tag in `tags`. Returns a map tag->float (or None if missing/invalid).
    """
    data = parse_information(cik, accn)

    # helper to recurse through dicts/lists and collect fact lists
    fact_lists: dict[str, list] = {}
    def collect(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, list) and v and isinstance(v[0], dict) and "value" in v[0]:
                    fact_lists[k] = v
                else:
                    collect(v)
        elif isinstance(o, list):
            for item in o:
                collect(item)

    collect(data)

    # extract
    result: dict[str, float | None] = {}
    for tag in tags:
        local = tag.split(":", 1)[-1]
        entries = fact_lists.get(tag) or fact_lists.get(local)
        val = None
        if isinstance(entries, list) and entries:
            raw_val = entries[0].get("value")
            try:
                val = float(raw_val) if raw_val not in (None, "") else None
            except (TypeError, ValueError):
                val = None
        result[tag] = val

    return result
