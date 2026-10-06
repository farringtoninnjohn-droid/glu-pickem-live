"""Append today's closing prices for the defense sim to defense-history.json.

Run by .github/workflows/defense-closes.yml after each U.S. market close.
Uses the same public quote service the page uses for live prices.
"""
import json, urllib.request, urllib.parse, datetime, zoneinfo, sys

END_DATE = "2026-11-06"
books = json.load(open("defense-books.json"))
tickers = sorted({h["t"] for b in books for h in b["holdings"]})

today = datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York")).date()
if today.weekday() >= 5 or today.isoformat() > END_DATE:
    print("Weekend or past the sim window; nothing to do."); sys.exit(0)

def fetch(symbols):
    url = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols="
           + urllib.parse.quote("|".join(symbols))
           + "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=0&output=json")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    out = {}
    for q in data["FormattedQuoteResult"]["FormattedQuote"]:
        last, when = q.get("last"), str(q.get("last_time") or "")
        if last and when.startswith(today.isoformat()):
            out[q["symbol"]] = float(str(last).replace(",", ""))
    return out

prices = fetch(tickers)
missing = [t for t in tickers if t not in prices]
if missing:                       # the service sometimes drops a symbol; ask again one by one
    for t in missing:
        prices.update(fetch([t]))
if not prices:
    print("No prices dated today (market holiday?); nothing written."); sys.exit(0)

hist = json.load(open("defense-history.json"))
hist["closes"][today.isoformat()] = {t: prices[t] for t in tickers if t in prices}
json.dump(hist, open("defense-history.json", "w"), indent=2)
print(f"Saved {len(prices)} closes for {today}; missing: {[t for t in tickers if t not in prices]}")
