# -*- coding: utf-8 -*-
import sys, json, datetime, os, re
import urllib.request, urllib.parse
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import requests

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]

KST_NOW = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
WEEKDAY_KOR = {"Mon":"월","Tue":"화","Wed":"수","Thu":"목","Fri":"금","Sat":"토","Sun":"일"}
TODAY = KST_NOW.strftime(f"%Y년 %m월 %d일 ({WEEKDAY_KOR.get(KST_NOW.strftime('%a'), '')})")

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_yf(ticker, period="2d", interval="1d"):
    try:
        hist = yf.Ticker(ticker).history(period=period, interval=interval)
        if len(hist) >= 2:
            prev, last = hist["Close"].iloc[-2], hist["Close"].iloc[-1]
            return last, (last - prev) / prev * 100
        elif len(hist) == 1:
            return hist["Close"].iloc[-1], 0.0
    except Exception:
        pass
    return None, None

def fetch_kr_market(index_code: str):
    try:
        r = requests.get(
            f"https://m.stock.naver.com/api/index/{index_code}/integration",
            headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
                     "Referer": "https://m.stock.naver.com", "Accept": "application/json"},
            timeout=10, verify=False)
        infos = {item["code"]: item["value"] for item in r.json().get("totalInfos", [])}
        raw = infos.get("accumulatedTradingValue", "")
        num = int(re.sub(r"[^0-9]", "", raw) or "0")
        return f"{num // 1000 / 1000:.3f}조"
    except Exception:
        return "-"

print("📡 데이터 수집 중...")
kospi_vol_str  = fetch_kr_market("KOSPI")
kosdaq_vol_str = fetch_kr_market("KOSDAQ")
kospi,    kospi_chg    = fetch_yf("^KS11")
kosdaq,   kosdaq_chg   = fetch_yf("^KQ11")
sp500,    sp500_chg    = fetch_yf("^GSPC")
nasdaq,   nasdaq_chg   = fetch_yf("^IXIC")
shanghai, shanghai_chg = fetch_yf("000001.SS")
dax,      dax_chg      = fetch_yf("^GDAXI")
wti,      wti_chg      = fetch_yf("CL=F")
gold,     gold_chg     = fetch_yf("GC=F")
btc,      btc_chg      = fetch_yf("BTC-USD")
vix,      vix_chg      = fetch_yf("^VIX")
usd_krw,  usdkrw_chg   = fetch_yf("KRW=X")
dxy,      dxy_chg      = fetch_yf("DX-Y.NYB")
us10y,    us10y_chg    = fetch_yf("^TNX")
us30y,    us30y_chg    = fetch_yf("^TYX")

def fv(val, dec=2):
    return f"{val:,.{dec}f}" if val is not None else "-"
def fc(chg):
    if chg is None: return "-"
    return f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"
def arrow(chg):
    if chg is None: return " "
    return "▲" if chg > 0 else ("▼" if chg < 0 else " ")

SEP = "─" * 52
lines = [
    f"\n{'='*52}",
    f"  📊 시장 상황 리포트  {TODAY}",
    f"{'='*52}",
    f"  {'지표':<17} {'현재값':>11}  {'등락':>8}",
    SEP,
    f"  {'코스피':<17} {fv(kospi):>11}  {arrow(kospi_chg)} {fc(kospi_chg):>8}",
    f"  {'  └ 거래대금':<17} {kospi_vol_str:>11}",
    f"  {'코스닥':<17} {fv(kosdaq):>11}  {arrow(kosdaq_chg)} {fc(kosdaq_chg):>8}",
    f"  {'  └ 거래대금':<17} {kosdaq_vol_str:>11}",
    f"  {'S&P 500':<17} {fv(sp500):>11}  {arrow(sp500_chg)} {fc(sp500_chg):>8}",
    f"  {'나스닥':<17} {fv(nasdaq):>11}  {arrow(nasdaq_chg)} {fc(nasdaq_chg):>8}",
    f"  {'상하이':<17} {fv(shanghai):>11}  {arrow(shanghai_chg)} {fc(shanghai_chg):>8}",
    f"  {'DAX':<17} {fv(dax):>11}  {arrow(dax_chg)} {fc(dax_chg):>8}",
    SEP,
    f"  {'WTI ($/bbl)':<17} {fv(wti):>11}  {arrow(wti_chg)} {fc(wti_chg):>8}",
    f"  {'Gold ($/oz)':<17} {fv(gold):>11}  {arrow(gold_chg)} {fc(gold_chg):>8}",
    f"  {'비트코인 (USD)':<17} {fv(btc,0):>11}  {arrow(btc_chg)} {fc(btc_chg):>8}",
    f"  {'VIX':<17} {fv(vix):>11}  {arrow(vix_chg)} {fc(vix_chg):>8}",
    SEP,
    f"  {'원/달러':<17} {fv(usd_krw):>11}  {arrow(usdkrw_chg)} {fc(usdkrw_chg):>8}",
    f"  {'달러인덱스':<17} {fv(dxy,3):>11}  {arrow(dxy_chg)} {fc(dxy_chg):>8}",
    f"  {'美 10년물(%)':<17} {fv(us10y,3):>11}  {arrow(us10y_chg)} {fc(us10y_chg):>8}",
    f"  {'美 30년물(%)':<17} {fv(us30y,3):>11}  {arrow(us30y_chg)} {fc(us30y_chg):>8}",
    SEP,
    f"  ※ 기준: 전일 종가  |  생성: {KST_NOW.strftime('%Y-%m-%d %H:%M')} KST",
    f"\n📈 대시보드: https://neon-liger-ccc963.netlify.app/",
]
report = "\n".join(lines)
print(report)
send_telegram(report)
print("✅ 텔레그램 전송 완료")
