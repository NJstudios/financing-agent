import os, io, hashlib, httpx
from minio import Minio
from dotenv import load_dotenv

load_dotenv()  # ensures MINIO_* env vars are read

# initialise once
mc = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)

BUCKET = os.getenv("MINIO_BUCKET", "filings")
if not mc.bucket_exists(BUCKET):
    mc.make_bucket(BUCKET)


UA = {"User-Agent": os.getenv("USER_AGENT")}

def fetch_and_store(cik: str, accn: str) -> str:
    #build paths 
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}"
    idx    = f"{base}/index.json"
    manifest = httpx.get(idx, headers=UA, timeout=30).json() # getting the data through a get request to the specified path
    html_fn  = next(f["name"] for f in manifest["directory"]["item"]
                    if f["name"].lower().endswith((".htm","html"))) # finding the FIRST item that is a html or htm file, this contains the information we need
    html_url = f"{base}/{html_fn}" #final url

    # 2. Download with httpx.get (returns a Response)
    resp = httpx.get(html_url, headers=UA, timeout=60.0)
    resp.raise_for_status()

    # 3. Stream through the body in chunks to compute checksum + buffer
    hasher = hashlib.sha256()
    buffer = io.BytesIO()
    for chunk in resp.iter_bytes(chunk_size=5_242_880):  # ~5 MiB
        hasher.update(chunk)
        buffer.write(chunk)

    checksum = hasher.hexdigest()
    buffer.seek(0)

    #upload for storing to minIO
    mc.put_object(
        BUCKET,
        f"raw/{accn}.html",
        buffer,
        buffer.getbuffer().nbytes,
        content_type="text/html"
    )

    return checksum