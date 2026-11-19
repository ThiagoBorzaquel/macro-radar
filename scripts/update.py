#!/usr/bin/env python3
"""Coleta dados públicos (Yahoo Finance chart, Banco Central SGS, RSS) e grava data/data.json."""
import json, urllib.request, urllib.parse, xml.etree.ElementTree as ET, email.utils, datetime as dt
from concurrent.futures import ThreadPoolExecutor
UA = {"User-Agent": "Mozilla/5.0 (compatible; MacroRadar/1.0)"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20).read()

# (símbolo, nome, região, grupo)
QUOTES = [
 ("^GSPC","S&P 500","eua","Índices"),("^DJI","Dow Jones","eua","Índices"),("^IXIC","Nasdaq","eua","Índices"),
 ("^RUT","Russell 2000","eua","Índices"),("^VIX","VIX","eua","Índices"),("^TNX","Treasury 10Y (%)","eua","Juros"),
 ("^BVSP","Ibovespa","brasil","Índices"),("BRL=X","Dólar (USD/BRL)","brasil","Câmbio"),("EURBRL=X","Euro (EUR/BRL)","brasil","Câmbio"),
 ("^FTSE","FTSE 100","europa","Índices"),("^GDAXI","DAX","europa","Índices"),("^FCHI","CAC 40","europa","Índices"),
 ("^STOXX50E","Euro Stoxx 50","europa","Índices"),("EURUSD=X","EUR/USD","europa","Câmbio"),
 ("^N225","Nikkei 225","asia","Índices"),("^HSI","Hang Seng","asia","Índices"),("000001.SS","Xangai","asia","Índices"),
 ("^KS11","Kospi","asia","Índices"),("^AXJO","ASX 200","asia","Índices"),("JPY=X","USD/JPY","asia","Câmbio"),
 ("CL=F","Petróleo WTI","mundo","Commodities"),("BZ=F","Petróleo Brent","mundo","Commodities"),("GC=F","Ouro","mundo","Commodities"),
 ("BTC-USD","Bitcoin","mundo","Cripto"),("ETH-USD","Ethereum","mundo","Cripto"),
]
def quote(q):
    sym, name, region, group = q
    try:
        j = json.loads(get("https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(sym)+"?range=1d&interval=15m"))
        r = j["chart"]["result"][0]; m = r["meta"]
        p, prev = m["regularMarketPrice"], m.get("chartPreviousClose") or m.get("previousClose")
        closes = [round(c, 4) for c in r["indicators"]["quote"][0]["close"] if c is not None]
        return dict(sym=sym, name=name, region=region, group=group, price=p, prev=prev,
                    chg=(p-prev) if prev else None, pct=((p/prev-1)*100) if prev else None, spark=closes[-40:])
    except Exception as e:
        print("erro", sym, e); return None

BCB = [(432,"Selic (meta, % a.a.)"),(433,"IPCA (mensal, %)"),(13522,"IPCA (12 meses, %)"),(1,"Dólar PTAX venda (R$)")]
def bcb(s):
    try:
        d = json.loads(get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{s[0]}/dados/ultimos/1?formato=json"))[0]
        return dict(name=s[1], value=float(d["valor"]), date=d["data"])
    except Exception as e:
        print("erro bcb", s, e); return None

GN = "https://news.google.com/rss/search?q={}&hl={}&gl={}&ceid={}"
FEEDS = [
 ("https://feeds.bbci.co.uk/news/business/rss.xml","BBC Business","mundo"),
 ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258","CNBC Economy","eua"),
 ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664","CNBC Finance","eua"),
 ("https://g1.globo.com/rss/g1/economia/","G1 Economia","brasil"),
 ("https://www.infomoney.com.br/feed/","InfoMoney","brasil"),
 (GN.format("Federal+Reserve+OR+Wall+Street+OR+US+economy","en-US","US","US:en"),"Google News EUA","eua"),
 (GN.format("Ibovespa+OR+Selic+OR+Banco+Central+OR+economia+brasileira","pt-BR","BR","BR:pt-419"),"Google News Brasil","brasil"),
 (GN.format("ECB+OR+eurozone+OR+European+economy","en-GB","GB","GB:en"),"Google News Europa","europa"),
 (GN.format("China+economy+OR+Nikkei+OR+Asia+markets","en-US","US","US:en"),"Google News Ásia","asia"),
]
def feed(f):
    url, src, region = f; out = []
    try:
        for it in ET.fromstring(get(url)).iter("item"):
            t = (it.findtext("title") or "").strip(); l = (it.findtext("link") or "").strip()
            try: d = email.utils.parsedate_to_datetime(it.findtext("pubDate")).astimezone(dt.timezone.utc)
            except Exception: continue
            if t and l: out.append(dict(title=t, url=l, source=src, region=region, ts=d.isoformat()))
    except Exception as e:
        print("erro feed", src, e)
    return out[:25]

with ThreadPoolExecutor(12) as ex:
    quotes = [q for q in ex.map(quote, QUOTES) if q]
    macro = [m for m in ex.map(bcb, BCB) if m]
    news, seen = [], set()
    for lst in ex.map(feed, FEEDS):
        for n in lst:
            k = n["title"].lower()[:60]
            if k not in seen: seen.add(k); news.append(n)
news.sort(key=lambda n: n["ts"], reverse=True)
json.dump(dict(updated=dt.datetime.now(dt.timezone.utc).isoformat(), quotes=quotes, macro=macro, news=news[:150]),
          open("data/data.json","w"), ensure_ascii=False, separators=(",",":"))
print(len(quotes), "cotações,", len(news), "notícias")
