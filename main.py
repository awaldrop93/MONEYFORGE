"""
EntityLens (v1)
--------------------------------------
Normalizes free public SEC EDGAR data into one clean REST endpoint:
give it a company name, ticker, or CIK, get back a simple JSON summary
of who the entity is and its most recent filings.

Deploy anywhere that can run a Python ASGI app (Render, Railway, Fly.io
free tiers all work) or adapt _resolve_cik/lookup into a serverless
function. No API key required for v1.

IMPORTANT: the SEC requires a descriptive User-Agent header with a real
contact email on every request (see
https://www.sec.gov/os/webmaster-faq#developers). Set the
SEC_CONTACT_EMAIL environment variable to a real address before
deploying, or SEC may throttle/block requests from the default value.

v1.1 will add SAM.gov federal exclusion status once a free SAM.gov API
key exists (see README.md "Next owner step").
"""
import os
import time
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

SEC_CONTACT_EMAIL = os.environ.get("SEC_CONTACT_EMAIL", "set-me@example.com")
HEADERS = {"User-Agent": f"MoneyForge Compliance Lookup API ({SEC_CONTACT_EMAIL})"}

app = FastAPI(
    title="EntityLens",
    version="0.1.0",
    description="Clean REST lookup over free public SEC EDGAR company data.",
)

_ticker_cache = {"data": None, "fetched_at": 0.0}
TICKER_CACHE_TTL = 6 * 60 * 60  # 6 hours


async def _load_ticker_map():
    """SEC publishes a single JSON file mapping every public company's
    ticker/name to its CIK. Cache it in memory so we don't refetch on
    every request."""
    now = time.time()
    if _ticker_cache["data"] and now - _ticker_cache["fetched_at"] < TICKER_CACHE_TTL:
        return _ticker_cache["data"]
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS)
        resp.raise_for_status()
        raw = resp.json()
    by_name, by_ticker = {}, {}
    for entry in raw.values():
        cik = str(entry["cik_str"]).zfill(10)
        by_ticker[entry["ticker"].upper()] = cik
        by_name[entry["title"].upper()] = cik
    _ticker_cache["data"] = {"by_name": by_name, "by_ticker": by_ticker}
    _ticker_cache["fetched_at"] = now
    return _ticker_cache["data"]


async def _resolve_cik(company: Optional[str], ticker: Optional[str], cik: Optional[str]):
    if cik:
        return str(cik).zfill(10)
    maps = await _load_ticker_map()
    if ticker and ticker.upper() in maps["by_ticker"]:
        return maps["by_ticker"][ticker.upper()]
    if company:
        key = company.upper()
        if key in maps["by_name"]:
            return maps["by_name"][key]
        for name, c in maps["by_name"].items():
            if key in name:
                return c
    return None


@app.get("/")
async def root():
    return {
        "service": "EntityLens",
        "status": "ok",
        "docs": "/docs",
        "lookup_example": "/lookup?ticker=AAPL",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/lookup")
async def lookup(
    company: str = Query(None, description="Company name, e.g. 'Apple Inc'"),
    ticker: str = Query(None, description="Stock ticker, e.g. 'AAPL'"),
    cik: str = Query(None, description="SEC CIK number if already known"),
):
    if not (company or ticker or cik):
        raise HTTPException(400, "Provide one of: company, ticker, or cik")

    resolved_cik = await _resolve_cik(company, ticker, cik)
    if not resolved_cik:
        raise HTTPException(404, "No matching SEC-registered entity found")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://data.sec.gov/submissions/CIK{resolved_cik}.json", headers=HEADERS
        )
    if resp.status_code == 404:
        raise HTTPException(404, "CIK not found in SEC EDGAR")
    resp.raise_for_status()
    data = resp.json()

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accns = recent.get("accessionNumber", [])
    filings = [
        {
            "form": forms[i],
            "filed": dates[i] if i < len(dates) else None,
            "accession_number": accns[i] if i < len(accns) else None,
        }
        for i in range(min(5, len(forms)))
    ]

    return JSONResponse(
        {
            "cik": resolved_cik,
            "name": data.get("name"),
            "tickers": data.get("tickers", []),
            "exchanges": data.get("exchanges", []),
            "sic_description": data.get("sicDescription"),
            "filer_category": data.get("category"),
            "state_of_incorporation": data.get("stateOfIncorporation"),
            "recent_filings": filings,
            "sam_exclusion_status": "not_checked_in_v1 - requires a free SAM.gov API key, planned for v1.1",
            "source": ["SEC EDGAR (data.sec.gov)"],
        }
    )
