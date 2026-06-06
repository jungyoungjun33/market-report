# -*- coding: utf-8 -*-
import json, datetime, os, re
import urllib.request
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import requests

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
DASHBOARD_URL      = "https://splendorous-empanada-694d4e.netlify.app/"

KST_NOW     = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
WEEKDAY_KOR = {"Mon":"월","Tue":"화","Wed":"수","Thu":"목","Fri":"금","Sat":"토","Sun":"일"}
TODAY       = KST_NOW.strftime(f"%Y년 %m월 %d일 ({WEEKDAY_KOR.get(KST_NOW.strftime('%a'), '')})")
TODAY_LABEL = KST_NOW.strftime("%m-%d")
TODAY_FULL  = KST_NOW.strftime("%Y-%m-%d")

# (label, chart_id, unit, decimal)
METRICS = [
    ('코스피',        'c_kospi',  '',  2),
    ('코스닥',        'c_kosdaq', '',  2),
    ('코스피 거래대금', 'c_kpvol',  '조', 3),
    ('코스닥 거래대금', 'c_kqvol',  '조', 3),
    ('S&P 500',     'c_sp500',  '',  2),
    ('나스닥',        'c_nasdaq', '',  2),
    ('상하이',        'c_sh',     '',  2),
    ('DAX',         'c_dax',    '',  2),
    ('WTI',         'c_wti',    '$', 2),
    ('Gold',        'c_gold',   '$', 2),
    ('비트코인',      'c_btc',    '$', 0),
    ('VIX',         'c_vix',    '',  2),
    ('원/달러',       'c_usd',    '',  2),
    ('달러인덱스',     'c_dxy',    '',  3),
    ('美 10년물',     'c_us10',   '%', 3),
    ('美 30년물',     'c_us30',   '%', 3),
]


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def fetch_yf(ticker, period="2d", interval="1d"):
    try:
        hist = yf.Ticker(ticker).history(period=period, interval=interval)
        if len(hist) >= 2:
            prev = float(hist["Close"].iloc[-2])
            last = float(hist["Close"].iloc[-1])
            return prev, last, (last - prev) / prev * 100
        elif len(hist) == 1:
            last = float(hist["Close"].iloc[-1])
            return last, last, 0.0
    except Exception:
        pass
    return None, None, None


def fetch_kr_market(index_code):
    try:
        r = requests.get(
            f"https://m.stock.naver.com/api/index/{index_code}/integration",
            headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
                     "Referer": "https://m.stock.naver.com", "Accept": "application/json"},
            timeout=10, verify=False)
        infos = {item["code"]: item["value"] for item in r.json().get("totalInfos", [])}
        raw = infos.get("accumulatedTradingValue", "")
        num = int(re.sub(r"[^0-9]", "", raw) or "0")
        return num // 1000 / 1000
    except Exception:
        return None


def fmt_val(v):
    """Format value for chart data array"""
    if v is None: return 'null'
    if v == int(v) and abs(v) < 1e9:
        return str(int(v))
    return f'{v:.4f}'.rstrip('0').rstrip('.')


def fv(val, dec=2):
    return f"{val:,.{dec}f}" if val is not None else "-"

def fc(chg):
    if chg is None: return "-"
    return f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"

def arrow(chg):
    if chg is None: return " "
    return "▲" if chg > 0 else ("▼" if chg < 0 else " ")


def read_chart_data(content, chart_id):
    m = re.search(rf"getElementById\('{chart_id}'\).*?label:'[^']*',data:\[(.*?)\]",
                  content, re.DOTALL)
    if not m:
        return []
    vals = []
    for t in m.group(1).split(','):
        t = t.strip()
        if t == 'null':
            vals.append(None)
        elif t:
            try:
                vals.append(float(t))
            except ValueError:
                pass
    return vals


def build_table_row(label, prev_v, today_v, unit, dec):
    if prev_v is not None and today_v is not None and prev_v != 0:
        chg_pct = (today_v - prev_v) / prev_v * 100
    else:
        chg_pct = None

    def fmt_num(v):
        if v is None: return '-'
        return f"{int(round(v)):,}" if dec == 0 else f"{v:,.{dec}f}"

    unit_tag = f'<small>{unit}</small>' if unit else '<small></small>'

    if chg_pct is None:
        chg_html = '<span style="color:#64748b">-</span>'
    elif chg_pct > 0:
        chg_html = f'<span style="color:#ef4444">▲ {chg_pct:.2f}%</span>'
    elif chg_pct < 0:
        chg_html = f'<span style="color:#3b82f6">▼ {abs(chg_pct):.2f}%</span>'
    else:
        chg_html = f'<span style="color:#64748b">- 0.00%</span>'

    return (
        f'      <tr>\n'
        f'        <td class="lbl">{label}</td>\n'
        f'        <td class="num">{fmt_num(prev_v)}{unit_tag}</td>\n'
        f'        <td class="num">{fmt_num(today_v)}{unit_tag}</td>\n'
        f'        <td class="chg">{chg_html}</td>\n'
        f'      </tr>'
    )


def update_dashboard(chart_values):
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse labels
    labels_m = re.search(r'labels:\s*(\["[^"]*"(?:,\s*"[^"]*")*\])', content)
    if not labels_m:
        print("⚠️ labels 파싱 실패")
        return

    labels = json.loads(labels_m.group(1))
    already_exists = TODAY_LABEL in labels

    # Determine prev date and read prev values BEFORE updating
    if already_exists:
        prev_label = labels[-2] if len(labels) >= 2 else labels[-1]
    else:
        prev_label = labels[-1]
    prev_date_full = f"{KST_NOW.strftime('%Y')}-{prev_label}"

    # Read prev values from chart data
    prev_chart_vals = {}
    for _, chart_id, _, _ in METRICS:
        vals = read_chart_data(content, chart_id)
        non_null = [v for v in vals if v is not None]
        if already_exists:
            prev_chart_vals[chart_id] = non_null[-2] if len(non_null) >= 2 else (non_null[-1] if non_null else None)
        else:
            prev_chart_vals[chart_id] = non_null[-1] if non_null else None

    # Update labels
    if not already_exists:
        labels.append(TODAY_LABEL)
        labels = labels[-30:]
    content = content.replace(labels_m.group(1), json.dumps(labels))

    # Update table header dates
    content = re.sub(
        r'(<th>📅 )\d{4}-\d{2}-\d{2}(</th>\s*<th>📅 )\d{4}-\d{2}-\d{2}(</th>)',
        rf'\g<1>{prev_date_full}\g<2>{TODAY_FULL}\g<3>',
        content
    )

    # Regenerate tbody
    rows = [build_table_row(label, prev_chart_vals.get(cid), chart_values.get(cid), unit, dec)
            for label, cid, unit, dec in METRICS]
    new_tbody = '    <tbody>\n      \n' + '\n      \n'.join(rows) + '\n    </tbody>'
    content = re.sub(r'<tbody>.*?</tbody>', new_tbody, content, flags=re.DOTALL)

    # Update chart data arrays
    def update_block(block, new_val):
        if new_val is None:
            return block
        def replacer(m):
            vals = []
            for t in m.group(2).split(','):
                t = t.strip()
                if t == 'null':
                    vals.append(None)
                elif t:
                    try:
                        vals.append(float(t))
                    except ValueError:
                        pass
            if already_exists:
                if vals: vals[-1] = new_val
            else:
                vals.append(new_val)
                vals = vals[-30:]
            return m.group(1) + ','.join(fmt_val(v) for v in vals) + m.group(3)
        return re.sub(r"(label:'[^']*',data:\[)(.*?)(\])", replacer, block)

    parts = re.split(r'(?=new Chart\()', content)
    result = [parts[0]]
    for part in parts[1:]:
        id_m = re.search(r"getElementById\('([^']+)'\)", part)
        if id_m and id_m.group(1) in chart_values:
            part = update_block(part, chart_values[id_m.group(1)])
        result.append(part)
    content = ''.join(result)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 대시보드 업데이트 완료 ({TODAY_LABEL})")


# ── 데이터 수집 ─────────────────────────────────────────────
print("📡 데이터 수집 중...")
kospi_prev,  kospi,   kospi_chg  = fetch_yf("^KS11")
kosdaq_prev, kosdaq,  kosdaq_chg = fetch_yf("^KQ11")
sp500_prev,  sp500,   sp500_chg  = fetch_yf("^GSPC")
nasdaq_prev, nasdaq,  nasdaq_chg = fetch_yf("^IXIC")
sh_prev,     shanghai,sh_chg     = fetch_yf("000001.SS")
dax_prev,    dax,     dax_chg    = fetch_yf("^GDAXI")
wti_prev,    wti,     wti_chg    = fetch_yf("CL=F")
gold_prev,   gold,    gold_chg   = fetch_yf("GC=F")
btc_prev,    btc,     btc_chg    = fetch_yf("BTC-USD")
vix_prev,    vix,     vix_chg    = fetch_yf("^VIX")
usd_prev,    usd_krw, usdkrw_chg = fetch_yf("KRW=X")
dxy_prev,    dxy,     dxy_chg    = fetch_yf("DX-Y.NYB")
us10_prev,   us10y,   us10y_chg  = fetch_yf("^TNX")
us30_prev,   us30y,   us30y_chg  = fetch_yf("^TYX")
kospi_vol  = fetch_kr_market("KOSPI")
kosdaq_vol = fetch_kr_market("KOSDAQ")

update_dashboard({
    'c_kospi':  kospi,
    'c_kosdaq': kosdaq,
    'c_kpvol':  kospi_vol,
    'c_kqvol':  kosdaq_vol,
    'c_sp500':  sp500,
    'c_nasdaq': nasdaq,
    'c_sh':     shanghai,
    'c_dax':    dax,
    'c_wti':    wti,
    'c_gold':   gold,
    'c_btc':    btc,
    'c_vix':    vix,
    'c_usd':    usd_krw,
    'c_dxy':    dxy,
    'c_us10':   us10y,
    'c_us30':   us30y,
})

# ── 텔레그램 리포트 ──────────────────────────────────────────
def vol_str(v):
    return f"{v:.3f}조" if v is not None else "-"

SEP = "─" * 52
lines = [
    f"\n{'='*52}",
    f"  📊 시장 상황 리포트  {TODAY}",
    f"{'='*52}",
    f"  {'지표':<17} {'현재값':>11}  {'등락':>8}",
    SEP,
    f"  {'코스피':<17} {fv(kospi):>11}  {arrow(kospi_chg)} {fc(kospi_chg):>8}",
    f"  {'  └ 거래대금':<17} {vol_str(kospi_vol):>11}",
    f"  {'코스닥':<17} {fv(kosdaq):>11}  {arrow(kosdaq_chg)} {fc(kosdaq_chg):>8}",
    f"  {'  └ 거래대금':<17} {vol_str(kosdaq_vol):>11}",
    f"  {'S&P 500':<17} {fv(sp500):>11}  {arrow(sp500_chg)} {fc(sp500_chg):>8}",
    f"  {'나스닥':<17} {fv(nasdaq):>11}  {arrow(nasdaq_chg)} {fc(nasdaq_chg):>8}",
    f"  {'상하이':<17} {fv(shanghai):>11}  {arrow(sh_chg)} {fc(sh_chg):>8}",
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
    f"\n📈 대시보드: {DASHBOARD_URL}",
]
report = "\n".join(lines)
print(report)
send_telegram(report)
print("✅ 텔레그램 전송 완료")
