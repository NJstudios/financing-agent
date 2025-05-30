import os
import time
import httpx # type: ignore
import traceback
from dotenv import load_dotenv # type: ignore
from store_module import fetch_and_store
from parser import extract_tags
from db import store_filing, store_metrics

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
METRIC_TAG_MAP = {
    # Top‐line
    "revenue": [
        "us-gaap:Revenues",
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:SalesRevenueNet",
        "us-gaap:RevenuesNetOfInterestExpenseFinancingActivities"
    ],

    # Profitability
    "gross_profit": [
        "us-gaap:GrossProfit",
        "us-gaap:GrossProfitLoss"
    ],
    "operating_income": [
        "us-gaap:OperatingIncomeLoss",
        "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "us-gaap:OperatingIncomeLossBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
    ],
    "net_income": [
        "us-gaap:NetIncomeLoss",
        "us-gaap:ProfitLoss"
    ],

    # Cash flow
    "operating_cash_flow": [
        "us-gaap:NetCashProvidedByUsedInOperatingActivities",
        "us-gaap:NetCashProvidedByOperatingActivities",
        "us-gaap:NetCashProvidedByUsedInContinuingOperatingActivities"
    ],
    "capital_expenditures": [
        "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
        "us-gaap:PurchaseOfPropertyPlantAndEquipment",
        "us-gaap:AcquisitionsNetOfCashAcquired"
    ],

    # Balance sheet
    "total_assets": [
        "us-gaap:Assets"
    ],
    "total_liabilities": [
        "us-gaap:Liabilities"
    ],
    "shareholders_equity": [
        "us-gaap:StockholdersEquity",
        "us-gaap:Equity"
    ],

    # Liquidity (optional extras)
    "current_assets": [
        "us-gaap:AssetsCurrent"
    ],
    "current_liabilities": [
        "us-gaap:LiabilitiesCurrent"
    ],
    "cash_and_equivalents": [
        "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "us-gaap:CashCashEquivalentsAndShortTermInvestments"
    ]
}


seen = set()

def normalize_metrics(facts: dict[str, float|None]) -> dict[str, float|None]:
    """
    Given a flat map tag->value, pick the first non-None
    value for each canonical metric.
    """
    normalized = {}
    for metric, tags in METRIC_TAG_MAP.items():
        val = None
        for tag in tags:
            if facts.get(tag) is not None:
                val = facts[tag]
                break
        normalized[metric] = val
    return normalized

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
                raw_facts = extract_tags(CIK, newest, GAAP_TAGS)  # all_tags = sum of METRIC_TAG_MAP values

                metrics = normalize_metrics(raw_facts)
                
                print("NORMALIZED METRICS:", metrics, flush=True)
                filing_id = store_filing(CIK, newest, form, sha)
                store_metrics(filing_id, metrics)
                print(f"✔ Stored metrics for filing_id={filing_id}", flush=True)
            except Exception as pe:
                print(f"PARSER ERROR ({pe.__class__.__name__}): {repr(pe)}", flush=True)
                traceback.print_exc()

        except Exception as e:
            print(f"POLLING ERROR ({e.__class__.__name__}): {repr(e)}", flush=True)
            traceback.print_exc()

        time.sleep(WAIT)
