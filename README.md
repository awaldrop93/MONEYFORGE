# MoneyForge Compliance Lookup API (v1)

A clean REST wrapper over free, public SEC EDGAR company data. Give it a
company name, ticker, or CIK; get back a normalized JSON summary instead
of wrestling with SEC's raw formats.

Tested locally against the live SEC EDGAR API on 2026-09-20 (ticker
lookup, fuzzy name lookup, missing-param and unknown-company error
handling all verified working).

## What this is for

This is the first live validation experiment for MONEYFORGE's business
portfolio: list it free on RapidAPI and see whether real developers find
and use it over 30 days, before investing more time in this idea.
$0 cost, no card needed for any of the steps below.

## Deploy it (owner steps — about 10 minutes, no card required)

1. **Create a free [Render](https://render.com) account** (no credit
   card required for the free tier — verify that's still true at
   signup, platform policies change).
2. Push this folder to a new GitHub repo (also free, no card), or use
   Render's "deploy from a public repo" flow.
3. In Render: **New > Web Service**, point it at the repo. Render
   auto-detects Python. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment variable:** `SEC_CONTACT_EMAIL` = a real email of
     yours (SEC requires a real contact in the User-Agent header on
     every request — this is their policy, not optional)
4. Deploy. Render's free web services spin down after 15 minutes idle
   (~1 minute to wake back up) and include 750 free instance-hours a
   month — plenty for a 30-day demand test.
5. Confirm it works: visit `https://<your-app>.onrender.com/lookup?ticker=AAPL`

## List it on RapidAPI (owner step — this is the actual experiment)

1. Create a free RapidAPI provider account.
2. List a new API pointing at your deployed Render URL, with a free
   tier (e.g. 100 requests/day) and a paid tier if you want one.
3. RapidAPI will ask for payout details (bank info) to pay you when
   the API earns money — that's receiving money, not spending, but
   it's an account-creation step only you can do.
4. Note the listing date — that starts the 30-day clock on the
   validation experiment tracked on the MONEYFORGE dashboard.

## v1.1 (not built yet — needs one more free account)

SAM.gov federal exclusion status isn't included yet. It requires a free
personal API key from sam.gov (Account Details page, no card, but rate
limited to 10 requests/day without a "role" — 1,000/day with one). Once
you have that key, this can be added as a second data source in the
`/lookup` response.

## Files

- `main.py` — the FastAPI app
- `requirements.txt` — Python dependencies
