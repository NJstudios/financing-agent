import os, time, httpx
from dotenv import load_dotenv
from store_module import fetch_and_store


load_dotenv()
CIK  = os.getenv("CIK").zfill(10) #key for the SEC
URL  = f"https://data.sec.gov/submissions/CIK{CIK}.json" #url we get data from
UA   = {"User-Agent": os.getenv("USER_AGENT")} # our user
WAIT = int(os.getenv("POLL_INTERVAL", "600")) #  wait time

seen = set()

if __name__ == "__main__":
    while True:
        try:
            r = httpx.get(URL, headers=UA, timeout=30) #sending a get request
            if r.status_code == 429: # sending too many request
                print("SEC TIMEOUT")
                time.sleep(60)
                continue
            r.raise_for_status()
            newest = r.json()["filings"]["recent"]["accessionNumber"][0] #getting the first accession which will be the newest
            if newest not in seen: 

                print("Recieved new Filing: ", newest, flush=True)
                seen.add(newest) # reporting and storing new filing for use 

                # ── Stage 2: fetch & store ──
                sha = fetch_and_store(CIK, newest)
                print("ARCHIVED SHA-256:", sha, flush=True)
                
        except Exception as e: #error checking 
            print("polling error: ", e, flush=True)

        time.sleep(WAIT) #waiting before checking for new DATA
