"""Collect recent news headlines and SEC filings for the tickers in portfolio-tickers.json.

Writes portfolio-news.json. Run by .github/workflows/portfolio-news.yml, which saves the
result to the `portfolio-data` branch so the main branch (and the NFL page) stay untouched.
"""
import json, urllib.request, urllib.parse, email.utils, datetime, re, sys
import xml.etree.ElementTree as ET

UA = {"User-Agent": "glu-pickem-live portfolio tracker farringtoninnjohn@gmail.com"}
now = datetime.datetime.now(datetime.timezone.utc)
cutoff = now - datetime.timedelta(days=21)

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()

def news(t):
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(t["q"] + " when:21d")
           + "&hl=en-US&gl=US&ceid=US:en")
    items = []
    for it in ET.fromstring(get(url)).iter("item"):
        title = (it.findtext("title") or "").strip()
        src = it.find("source")
        source = src.text.strip() if src is not None and src.text else ""
        if source and title.endswith(" - " + source):
            title = title[: -len(" - " + source)]
        try:
            when = email.utils.parsedate_to_datetime(it.findtext("pubDate"))
        except Exception:
            continue
        if when < cutoff:
            continue
        items.append({"t": t["t"], "kind": "news", "title": title, "url": it.findtext("link"),
                      "source": source, "time": when.astimezone(datetime.timezone.utc).isoformat()})
    return items

def filings(t):
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=" + t["t"]
           + "&type=&dateb=&owner=include&count=15&output=atom")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(get(url)).findall("a:entry", ns):
        cat = e.find("a:category", ns)
        form = cat.get("term") if cat is not None else ""
        if form in ("4", "3", "5", "144", "SC 13G/A"):   # skip routine insider paperwork
            continue
        when = e.findtext("a:updated", default="", namespaces=ns)
        try:
            dt = datetime.datetime.fromisoformat(when)
        except Exception:
            continue
        if dt < cutoff:
            continue
        link = e.find("a:link", ns)
        out.append({"t": t["t"], "kind": "filing", "title": f"SEC filing: Form {form}",
                    "url": link.get("href") if link is not None else "", "source": "SEC EDGAR",
                    "time": dt.astimezone(datetime.timezone.utc).isoformat()})
    return out

tickers = json.load(open("portfolio-tickers.json"))
all_items, errors = [], []
for t in tickers:
    for fn in (news, filings):
        try:
            all_items += fn(t)
        except Exception as ex:
            errors.append(f"{t['t']} {fn.__name__}: {ex}")

seen, items = set(), []
for it in sorted(all_items, key=lambda x: x["time"], reverse=True):
    key = (it["t"], re.sub(r"\W+", "", it["title"].lower())[:60])
    if key in seen:
        continue
    seen.add(key)
    items.append(it)

per, capped = {}, []
for it in items:                      # keep at most 25 items per ticker
    per[it["t"]] = per.get(it["t"], 0) + 1
    if per[it["t"]] <= 25:
        capped.append(it)
items = capped
json.dump({"updated": now.isoformat(), "errors": errors, "items": items}, open("portfolio-news.json", "w"), indent=1)
print(len(items), "items;", "errors:", errors)
