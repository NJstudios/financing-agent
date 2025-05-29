import os, time, datetime as dt

interval = int(os.getenv("HEARTBEAT_INTERVAL", "5"))

if __name__ == "__main__":
    while True:
        print("💓  ingest container alive at", dt.datetime.utcnow().isoformat(), flush=True)
        time.sleep(interval)
