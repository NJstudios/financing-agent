import os
import time
import httpx
import traceback
from dotenv import load_dotenv
from store_module import fetch_and_store
from parser import extract_tags

load_dotenv()
CIK   = os.getenv("CIK").zfill(10)
URL   = f"https://data.sec.gov/submissions/CIK{CIK}.json"
UA    = {"User-Agent": os.getenv("USER_AGENT")}
WAIT  = int(os.getenv("POLL_INTERVAL", "600"))
ALLOWED = {"10-Q", "10-K"}

GAAP_TAGS = [
    "us-gaap:Revenues",
    "us-gaap:GrossProfit",
    "us-gaap:OperatingIncomeLoss",
    "us-gaap:NetIncomeLoss",
    "us-gaap:NetCashProvidedByUsedInOperatingActivities",
    "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
    "us-gaap:Assets",
    "us-gaap:Liabilities",
    "us-gaap:StockholdersEquity",
]

seen = set()

if __name__ == "__main__":
    while True:
        try:
            # 1) Poll SEC
            r = httpx.get(URL, headers=UA, timeout=30)
            if r.status_code == 429:
                print("SEC TIMEOUT", flush=True)
                time.sleep(60)
                continue
            r.raise_for_status()

            docs      = r.json()["filings"]["recent"]
            accs      = docs["accessionNumber"]
            forms     = docs["form"]

            # 2) Pick first unseen 10-Q or 10-K
            newest = None
            for accn, form in zip(accs, forms):
                if accn in seen:
                    continue
                if form not in ALLOWED:
                    continue
                newest = accn
                break

            if not newest:
                time.sleep(WAIT)
                continue

            print("Received new Filing:", newest, flush=True)
            seen.add(newest)

            # 3) Archive raw HTML
            sha = fetch_and_store(CIK, newest)
            print("ARCHIVED SHA-256:", sha, flush=True)

            # 4) Parse only guaranteed-XBRL forms
            try:
                facts = extract_tags(CIK, newest, GAAP_TAGS)
                print("PARSED FACTS:", facts, flush=True)
            except Exception as pe:
                print(f"PARSER ERROR ({pe.__class__.__name__}): {repr(pe)}", flush=True)
                traceback.print_exc()

        except Exception as e:
            print(f"POLLING ERROR ({e.__class__.__name__}): {repr(e)}", flush=True)
            traceback.print_exc()

        time.sleep(WAIT)
