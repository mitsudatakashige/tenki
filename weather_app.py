import streamlit as st
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
import folium
from streamlit_folium import st_folium
import datetime
import io
import math
import os
import urllib.request

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
FONT = "HeiseiKakuGo-W5"

# 日本語フォント設定
_font_path = "/tmp/NotoSansJP-Regular.ttf"
if not os.path.exists(_font_path):
    try:
        urllib.request.urlretrieve(
            "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf",
            _font_path
        )
    except:
        pass

from matplotlib import font_manager as _fm
if os.path.exists(_font_path):
    _fm.fontManager.addfont(_font_path)
    _prop = _fm.FontProperties(fname=_font_path)
    rcParams["font.family"] = _prop.get_name()
else:
    rcParams["font.family"] = "sans-serif"
    rcParams["font.sans-serif"] = ["Hiragino Sans", "IPAGothic", "DejaVu Sans"]

# ==============================
# 観測所マスタ
# ==============================
@st.cache_data(ttl=86400)
def load_station_master():
    stations = {}

    # アメダス観測所JSON取得
    try:
        r = requests.get(
            "https://www.jma.go.jp/bosai/amedas/const/amedastable.json",
            timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        amedas_data = r.json()
        for code, info in amedas_data.items():
            name = info.get("kjName", "") or info.get("enName", code)
            lat_deg = info.get("lat", [0, 0])
            lon_deg = info.get("lon", [0, 0])
            if isinstance(lat_deg, list) and len(lat_deg) >= 2:
                lat = lat_deg[0] + lat_deg[1] / 60.0
                lon = lon_deg[0] + lon_deg[1] / 60.0
            else:
                continue
            stations[name] = {
                "prec_no": None, "block_no": None,
                "amedas_code": code, "lat": lat, "lon": lon, "type": "amedas"
            }
    except:
        pass

    # 主要観測所（上書き）
    major = {
        "稚内": {"prec_no": "11", "block_no": "47401", "lat": 45.4158, "lon": 141.6806},
        "旭川": {"prec_no": "12", "block_no": "47407", "lat": 43.7706, "lon": 142.3650},
        "網走": {"prec_no": "13", "block_no": "47409", "lat": 44.0194, "lon": 144.2789},
        "釧路": {"prec_no": "16", "block_no": "47418", "lat": 42.9847, "lon": 144.3753},
        "帯広": {"prec_no": "16", "block_no": "47417", "lat": 42.9242, "lon": 143.2106},
        "札幌": {"prec_no": "14", "block_no": "47412", "lat": 43.0595, "lon": 141.3386},
        "函館": {"prec_no": "18", "block_no": "47430", "lat": 41.8158, "lon": 140.7519},
        "室蘭": {"prec_no": "18", "block_no": "47423", "lat": 42.3150, "lon": 140.9736},
        "青森": {"prec_no": "31", "block_no": "47575", "lat": 40.8244, "lon": 140.7694},
        "盛岡": {"prec_no": "32", "block_no": "47584", "lat": 39.6956, "lon": 141.1544},
        "秋田": {"prec_no": "33", "block_no": "47582", "lat": 39.7175, "lon": 140.0997},
        "仙台": {"prec_no": "34", "block_no": "47590", "lat": 38.2597, "lon": 140.8997},
        "山形": {"prec_no": "35", "block_no": "47588", "lat": 38.2556, "lon": 140.3394},
        "福島": {"prec_no": "36", "block_no": "47595", "lat": 37.7608, "lon": 140.4739},
        "水戸": {"prec_no": "40", "block_no": "47629", "lat": 36.3814, "lon": 140.4664},
        "宇都宮": {"prec_no": "41", "block_no": "47615", "lat": 36.5497, "lon": 139.8703},
        "前橋": {"prec_no": "42", "block_no": "47624", "lat": 36.3914, "lon": 139.0636},
        "熊谷": {"prec_no": "43", "block_no": "47626", "lat": 36.1472, "lon": 139.3883},
        "東京": {"prec_no": "44", "block_no": "47662", "lat": 35.6894, "lon": 139.6917},
        "横浜": {"prec_no": "46", "block_no": "47670", "lat": 35.4478, "lon": 139.6425},
        "千葉": {"prec_no": "45", "block_no": "47682", "lat": 35.6050, "lon": 140.1233},
        "甲府": {"prec_no": "49", "block_no": "47638", "lat": 35.6639, "lon": 138.5689},
        "長野": {"prec_no": "48", "block_no": "47610", "lat": 36.6514, "lon": 138.1814},
        "新潟": {"prec_no": "54", "block_no": "47604", "lat": 37.9161, "lon": 139.0364},
        "富山": {"prec_no": "55", "block_no": "47607", "lat": 36.6953, "lon": 137.2114},
        "金沢": {"prec_no": "56", "block_no": "47605", "lat": 36.5661, "lon": 136.6561},
        "福井": {"prec_no": "57", "block_no": "47616", "lat": 36.0653, "lon": 136.2219},
        "静岡": {"prec_no": "50", "block_no": "47656", "lat": 34.9769, "lon": 138.3833},
        "名古屋": {"prec_no": "51", "block_no": "47636", "lat": 35.1667, "lon": 136.9667},
        "岐阜": {"prec_no": "52", "block_no": "47632", "lat": 35.3911, "lon": 136.7222},
        "津": {"prec_no": "53", "block_no": "47651", "lat": 34.7306, "lon": 136.5086},
        "大津": {"prec_no": "60", "block_no": "47761", "lat": 35.0042, "lon": 135.8686},
        "京都": {"prec_no": "61", "block_no": "47759", "lat": 35.0117, "lon": 135.7683},
        "大阪": {"prec_no": "62", "block_no": "47772", "lat": 34.6861, "lon": 135.5200},
        "神戸": {"prec_no": "63", "block_no": "47770", "lat": 34.6939, "lon": 135.1950},
        "奈良": {"prec_no": "64", "block_no": "47780", "lat": 34.6853, "lon": 135.8328},
        "和歌山": {"prec_no": "65", "block_no": "47777", "lat": 34.2261, "lon": 135.1675},
        "鳥取": {"prec_no": "69", "block_no": "47746", "lat": 35.5036, "lon": 134.2378},
        "松江": {"prec_no": "68", "block_no": "47741", "lat": 35.4681, "lon": 133.0506},
        "岡山": {"prec_no": "66", "block_no": "47768", "lat": 34.6619, "lon": 133.9350},
        "広島": {"prec_no": "67", "block_no": "47765", "lat": 34.3853, "lon": 132.4553},
        "山口": {"prec_no": "81", "block_no": "47784", "lat": 34.1861, "lon": 131.4711},
        "徳島": {"prec_no": "71", "block_no": "47895", "lat": 34.0658, "lon": 134.5594},
        "高松": {"prec_no": "72", "block_no": "47891", "lat": 34.3400, "lon": 134.0436},
        "松山": {"prec_no": "73", "block_no": "47887", "lat": 33.8394, "lon": 132.7656},
        "高知": {"prec_no": "74", "block_no": "47893", "lat": 33.5597, "lon": 133.5311},
        "福岡": {"prec_no": "82", "block_no": "47807", "lat": 33.5903, "lon": 130.3608},
        "佐賀": {"prec_no": "85", "block_no": "47813", "lat": 33.2642, "lon": 130.3006},
        "長崎": {"prec_no": "84", "block_no": "47817", "lat": 32.7503, "lon": 129.8775},
        "熊本": {"prec_no": "86", "block_no": "47819", "lat": 32.8031, "lon": 130.7006},
        "大分": {"prec_no": "87", "block_no": "47815", "lat": 33.2381, "lon": 131.6067},
        "宮崎": {"prec_no": "88", "block_no": "47830", "lat": 31.9111, "lon": 131.4239},
        "鹿児島": {"prec_no": "88", "block_no": "47827", "lat": 31.5606, "lon": 130.5578},
        "那覇": {"prec_no": "91", "block_no": "47936", "lat": 26.2044, "lon": 127.6883},
        "石垣島": {"prec_no": "95", "block_no": "47918", "lat": 24.3378, "lon": 124.1636},
        "宮古島": {"prec_no": "94", "block_no": "47927", "lat": 24.7878, "lon": 125.2811},
    }
    for name, info in major.items():
        info["type"] = "major"
        stations[name] = info

    return stations


def find_nearest_station(lat, lon, stations):
    best_name, best_dist = None, float("inf")
    for name, info in stations.items():
        d = math.sqrt((lat - info["lat"])**2 + (lon - info["lon"])**2)
        if d < best_dist:
            best_dist = d
            best_name = name
    return best_name, stations[best_name]


# ==============================
# データ取得
# ==============================
def fetch_weather_for_year(prec_no, block_no, year, month, day):
    url = (f"https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php"
           f"?prec_no={prec_no}&block_no={block_no}&year={year}&month={month}&view=p1")
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "utf-8"
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", {"id": "tablefix1"})
        if not table:
            return None
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if not cols:
                continue
            try:
                if int(cols[0].get_text(strip=True)) != day:
                    continue
            except:
                continue
            texts = [c.get_text(strip=True) for c in cols]
            def sf(s):
                try:
                    s = str(s).replace("//","").replace("]","").replace("[","")
                    s = s.replace("x","").replace("#","").replace("--","")
                    s = s.replace("\u00a0","").replace("\u25a0","").strip()
                    if s in ("", "-", "///", "×"): return None
                    return float(s)
                except:
                    return None
            # 列順: 0:日 1:気圧現地 2:気圧海面 3:降水量 4:最大1時間 5:最大10分
            # 6:平均気温 7:最高気温 8:最低気温 9:湿度 10:蒸気圧 11:平均風速 12:最大風速
            return {
                "precip": sf(texts[3]) if len(texts) > 3 else None,
                "rain_1h_max": sf(texts[4]) if len(texts) > 4 else None,
                "temp_avg": sf(texts[6]) if len(texts) > 6 else None,
                "temp_max": sf(texts[7]) if len(texts) > 7 else None,
                "temp_min": sf(texts[8]) if len(texts) > 8 else None,
                "wind_avg": sf(texts[11]) if len(texts) > 11 else None,
                "wind_max": sf(texts[12]) if len(texts) > 12 else None,
                "_raw": texts,
            }
        return None
    except:
        return None


def fetch_amedas_daily(amedas_code, year, month, day):
    try:
        date_str = f"{year}{month:02d}{day:02d}"
        total_precip = 0.0
        rain_1h_max = 0.0
        has_data = False
        for hour in range(24):
            url = f"https://www.jma.go.jp/bosai/amedas/data/point/{amedas_code}/{date_str}_{hour:02d}0000.json"
            try:
                r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code != 200:
                    continue
                data = r.json()
                for time_key, vals in data.items():
                    p1h = vals.get("precipitation1h")
                    if p1h and isinstance(p1h, list) and len(p1h) > 0:
                        try:
                            v = float(p1h[0])
                            total_precip += v
                            rain_1h_max = max(rain_1h_max, v)
                            has_data = True
                        except:
                            pass
            except:
                continue
        if has_data:
            return {
                "precip": round(total_precip, 1),
                "rain_1h_max": round(rain_1h_max, 1) if rain_1h_max > 0 else None,
                "temp_avg": None, "temp_max": None, "temp_min": None,
                "wind_avg": None, "wind_max": None, "_raw": [],
            }
        return None
    except:
        return None


# ==============================
# 集計
# ==============================
def analyze_data(records):
    valid = [r for r in records if r]
    n = len(valid)
    if n == 0:
        return None
    precips = [(r["precip"] if r["precip"] is not None else 0.0) for r in valid]
    rain_days = sum(1 for p in precips if p >= 1.0)
    rain_0 = sum(1 for p in precips if p < 1.0)
    rain_1_10 = sum(1 for p in precips if 1.0 <= p < 10.0)
    rain_10plus = sum(1 for p in precips if p >= 10.0)
    precip_max = round(max(precips), 1) if precips else None
    precip_avg_rain = round(sum(p for p in precips if p >= 1.0) / max(rain_days, 1), 1) if rain_days > 0 else 0.0
    rain_1h_list = [r["rain_1h_max"] for r in valid if r.get("rain_1h_max") is not None]
    temp_avgs = [r["temp_avg"] for r in valid if r["temp_avg"] is not None]
    temp_maxs = [r["temp_max"] for r in valid if r["temp_max"] is not None]
    temp_mins = [r["temp_min"] for r in valid if r["temp_min"] is not None]
    wind_avgs = [r["wind_avg"] for r in valid if r["wind_avg"] is not None]
    wind_maxs = [r["wind_max"] for r in valid if r["wind_max"] is not None]
    def avg(lst): return round(sum(lst)/len(lst), 1) if lst else None
    def mx(lst): return round(max(lst), 1) if lst else None
    def mn(lst): return round(min(lst), 1) if lst else None
    return {
        "n": n, "rain_days": rain_days, "rain_0": rain_0,
        "rain_1_10": rain_1_10, "rain_10plus": rain_10plus,
        "precip_max": precip_max, "precip_avg_rain": precip_avg_rain,
        "precips": precips,
        "rain_1h_list": rain_1h_list,
        "rain_1h_max": mx(rain_1h_list), "rain_1h_avg": avg(rain_1h_list),
        "temp_avg_mean": avg(temp_avgs), "temp_max_mean": avg(temp_maxs),
        "temp_min_mean": avg(temp_mins), "temp_max_max": mx(temp_maxs),
        "temp_max_min": mn(temp_maxs), "temp_min_max": mx(temp_mins),
        "temp_min_min": mn(temp_mins), "wind_avg_mean": avg(wind_avgs),
        "wind_max_mean": avg(wind_maxs), "wind_max_max": mx(wind_maxs),
        "records": valid,
    }


# ==============================
# グラフ
# ==============================
def make_precip_chart(result):
    fig, ax = plt.subplots(figsize=(5, 3))
    labels = ["雨なし\n(<1mm)", "小雨\n(1〜10mm)", "大雨\n(10mm以上)"]
    vals = [result["rain_0"], result["rain_1_10"], result["rain_10plus"]]
    bars = ax.bar(labels, vals, color=["#90CAF9", "#42A5F5", "#1565C0"], edgecolor="white", linewidth=1.5)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f"{val}回", ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax.set_ylabel("回数", fontsize=10)
    ax.set_title("降水量の分布", fontsize=12, fontweight="bold")
    ax.set_ylim(0, max(vals) * 1.3 + 1)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig); buf.seek(0)
    return buf


def make_temp_chart(result):
    records = result["records"]
    data = [(i, r["temp_max"], r["temp_min"], r["temp_avg"])
            for i, r in enumerate(records)
            if r["temp_max"] is not None and r["temp_min"] is not None]
    if not data:
        return None
    xs = [d[0] for d in data]
    temp_maxs = [d[1] for d in data]
    temp_mins = [d[2] for d in data]
    temp_avgs = [d[3] for d in data if d[3] is not None]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.fill_between(xs, temp_mins, temp_maxs, alpha=0.2, color="#FF7043", label="気温幅")
    ax.plot(xs, temp_maxs, "o-", color="#E53935", label=f"最高気温 (平均{result['temp_max_mean']}℃)", linewidth=2)
    ax.plot(xs, temp_mins, "o-", color="#1E88E5", label=f"最低気温 (平均{result['temp_min_mean']}℃)", linewidth=2)
    if len(temp_avgs) == len(xs):
        ax.plot(xs, temp_avgs, "o--", color="#43A047", label=f"平均気温 (平均{result['temp_avg_mean']}℃)", linewidth=1.5)
    ax.set_xticks(xs)
    cy = datetime.datetime.now().year
    ax.set_xticklabels([str(cy - len(records) + i + 1) for i in xs], fontsize=8)
    ax.set_ylabel("気温 (℃)", fontsize=10); ax.set_title("過去の気温推移", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig); buf.seek(0)
    return buf


def make_wind_chart(result):
    records = result["records"]
    data = [(i, r["wind_avg"], r["wind_max"])
            for i, r in enumerate(records)
            if r["wind_max"] is not None]
    if not data:
        return None
    xs = [d[0] for d in data]
    wind_maxs = [d[2] for d in data]
    wind_avgs = [d[1] for d in data if d[1] is not None]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(xs, wind_maxs, color="#78909C", alpha=0.7, label="最大風速")
    if len(wind_avgs) == len(xs):
        ax.plot(xs, wind_avgs, "o-", color="#E53935", label="平均風速", linewidth=2, zorder=5)
    ax.axhline(y=10, color="orange", linestyle="--", alpha=0.7, label="10m/s (テント注意)")
    ax.axhline(y=15, color="red", linestyle="--", alpha=0.7, label="15m/s (テント撤収)")
    ax.set_xticks(xs)
    cy = datetime.datetime.now().year
    ax.set_xticklabels([str(cy - len(records) + i + 1) for i in xs], fontsize=8)
    ax.set_ylabel("風速 (m/s)", fontsize=10); ax.set_title("過去の風速推移", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig); buf.seek(0)
    return buf


def wind_risk_label(v):
    if v is None: return "不明", "gray"
    if v >= 15: return "⚠️ 要注意（撤収検討）", "red"
    if v >= 10: return "🔶 注意（ペグ増し）", "orange"
    return "✅ 概ね安全", "green"

def rain_risk_label(rain_days, n):
    if n == 0: return "不明", "gray"
    ratio = rain_days / n
    if ratio >= 0.5: return "☔ 雨の可能性が高い", "red"
    if ratio >= 0.3: return "🌂 雨の可能性あり", "orange"
    return "☀️ 概ね晴れ傾向", "green"


# ==============================
# PDF生成
# ==============================
def create_pdf(station_name, target_date, result, precip_buf, temp_buf, wind_buf):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    now = datetime.datetime.now()
    ts = ParagraphStyle("T", fontName=FONT, fontSize=16, leading=22, spaceAfter=6, textColor=colors.HexColor("#1a3a5c"))
    hs = ParagraphStyle("H", fontName=FONT, fontSize=12, leading=18, spaceBefore=10, spaceAfter=4,
        textColor=colors.white, backColor=colors.HexColor("#1a3a5c"))
    bs = ParagraphStyle("B", fontName=FONT, fontSize=10, leading=16, spaceAfter=3)
    ss = ParagraphStyle("S", fontName=FONT, fontSize=9, leading=14, spaceAfter=2, textColor=colors.HexColor("#555555"))
    tbl_style = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,-1), FONT),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f0f4f8"), colors.white]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING", (0,0), (-1,-1), 5),
        ("ALIGN", (1,0), (-1,-1), "CENTER"),
    ])
    from reportlab.platypus import Image as RLImage
    c = []
    c.append(Spacer(1, 5*mm))
    c.append(Paragraph("過去気象データ集計レポート", ts))
    c.append(Paragraph(f"調査地点：{station_name}　対象日：{target_date}　（過去{result['n']}年分）", bs))
    c.append(Paragraph(f"作成日時：{now.strftime('%Y年%m月%d日 %H:%M')}", ss))
    c.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a3a5c")))
    c.append(Spacer(1, 5*mm))

    # ① 降雨
    c.append(Paragraph("　① 降雨", hs))
    c.append(Spacer(1, 2*mm))
    rain_label, _ = rain_risk_label(result["rain_days"], result["n"])
    c.append(Paragraph(f"判定：{rain_label}", bs))
    c.append(Spacer(1, 2*mm))
    c.append(Paragraph("【24時間降水量】", bs))
    rows = [["項目", "値"],
            ["雨だった日数", f"{result['rain_days']}回 / {result['n']}年"],
            ["最大降水量", f"{result['precip_max']} mm" if result.get('precip_max') else "―"],
            ["雨の日の平均降水量", f"{result['precip_avg_rain']} mm" if result['rain_days'] > 0 else "―"],
            ["雨なし（<1mm）", f"{result['rain_0']}回"],
            ["小雨（1〜10mm）", f"{result['rain_1_10']}回"],
            ["大雨（10mm以上）", f"{result['rain_10plus']}回"]]
    t = Table(rows, colWidths=[80*mm, 80*mm]); t.setStyle(tbl_style)
    c.append(t); c.append(Spacer(1, 3*mm))
    c.append(Paragraph("【最大1時間雨量】", bs))
    rows2 = [["項目", "値"],
             ["最大1時間雨量（最大値）", f"{result['rain_1h_max']} mm" if result.get('rain_1h_max') else "―"],
             ["最大1時間雨量（平均）", f"{result['rain_1h_avg']} mm" if result.get('rain_1h_avg') else "―"]]
    t2 = Table(rows2, colWidths=[80*mm, 80*mm]); t2.setStyle(tbl_style)
    c.append(t2); c.append(Spacer(1, 3*mm))
    if precip_buf:
        precip_buf.seek(0)
        c.append(RLImage(precip_buf, width=100*mm, height=60*mm))
    c.append(Spacer(1, 5*mm))

    # ② 気温
    c.append(Paragraph("　② 気温", hs))
    c.append(Spacer(1, 2*mm))
    rows = [["項目", "値"],
            ["平均気温（平均）", f"{result['temp_avg_mean']} ℃" if result['temp_avg_mean'] else "データなし"],
            ["最高気温（平均）", f"{result['temp_max_mean']} ℃" if result['temp_max_mean'] else "データなし"],
            ["最低気温（平均）", f"{result['temp_min_mean']} ℃" if result['temp_min_mean'] else "データなし"]]
    t = Table(rows, colWidths=[80*mm, 80*mm]); t.setStyle(tbl_style)
    c.append(t); c.append(Spacer(1, 3*mm))

    # ③ ばらつき
    c.append(Paragraph("　③ ばらつき（振れ幅）", hs))
    c.append(Spacer(1, 2*mm))
    rows = [["項目", "最大", "最小"],
            ["最高気温", f"{result['temp_max_max']} ℃" if result['temp_max_max'] else "-",
             f"{result['temp_max_min']} ℃" if result['temp_max_min'] else "-"],
            ["最低気温", f"{result['temp_min_max']} ℃" if result['temp_min_max'] else "-",
             f"{result['temp_min_min']} ℃" if result['temp_min_min'] else "-"]]
    t = Table(rows, colWidths=[60*mm, 55*mm, 55*mm]); t.setStyle(tbl_style)
    c.append(t); c.append(Spacer(1, 3*mm))
    if temp_buf:
        temp_buf.seek(0)
        c.append(RLImage(temp_buf, width=140*mm, height=80*mm))
    c.append(Spacer(1, 5*mm))

    # ④ 風
    c.append(Paragraph("　④ 風", hs))
    c.append(Spacer(1, 2*mm))
    wind_label, _ = wind_risk_label(result["wind_max_max"])
    c.append(Paragraph(f"テント判定：{wind_label}", bs))
    rows = [["項目", "値"],
            ["平均風速（平均）", f"{result['wind_avg_mean']} m/s" if result['wind_avg_mean'] else "データなし"],
            ["最大風速（平均）", f"{result['wind_max_mean']} m/s" if result['wind_max_mean'] else "データなし"],
            ["最大風速（最大値）", f"{result['wind_max_max']} m/s" if result['wind_max_max'] else "データなし"]]
    t = Table(rows, colWidths=[80*mm, 80*mm]); t.setStyle(tbl_style)
    c.append(t); c.append(Spacer(1, 3*mm))
    if wind_buf:
        wind_buf.seek(0)
        c.append(RLImage(wind_buf, width=140*mm, height=80*mm))

    c.append(Spacer(1, 5*mm))
    c.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
    c.append(Paragraph("※本レポートは気象庁過去データをもとに自動集計したものです。実際の気象条件は異なる場合があります。", ss))
    doc.build(c)
    buffer.seek(0)
    return buffer.getvalue()


# ==============================
# Streamlit UI
# ==============================
st.set_page_config(page_title="過去気象データ集計", page_icon="🌤️", layout="centered")
st.title("🌤️ 過去気象データ集計")
st.caption("地図をクリックして地点を選択し、日付を指定すると過去の気象データを集計します。")
st.divider()

with st.spinner("観測所データを読み込み中..."):
    STATION_MASTER = load_station_master()

for key, val in [("clicked_lat", None), ("clicked_lon", None),
                 ("station_name", None), ("weather_result", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# 地図
st.subheader("📍 地点を選択")
st.caption("地図をクリックすると最寄りの観測所が自動選択されます。濃い青●＝主要観測所（全項目）、薄い青●＝アメダス（降水量のみ）")

m = folium.Map(location=[36.0, 137.0], zoom_start=5)
for name, info in STATION_MASTER.items():
    is_major = info.get("type") == "major"
    folium.CircleMarker(
        location=[info["lat"], info["lon"]],
        radius=4 if is_major else 3,
        color="#1565C0" if is_major else "#90CAF9",
        fill=True, fill_opacity=0.6,
        tooltip=f"{name}（{'主要' if is_major else 'アメダス'}）"
    ).add_to(m)

if st.session_state["clicked_lat"]:
    folium.Marker(
        location=[st.session_state["clicked_lat"], st.session_state["clicked_lon"]],
        icon=folium.Icon(color="red", icon="home")
    ).add_to(m)

map_data = st_folium(m, width=700, height=400, returned_objects=["last_clicked"])

if map_data and map_data.get("last_clicked"):
    clat = map_data["last_clicked"]["lat"]
    clon = map_data["last_clicked"]["lng"]
    name, info = find_nearest_station(clat, clon, STATION_MASTER)
    st.session_state.update({
        "clicked_lat": clat, "clicked_lon": clon,
        "station_name": name, "station_info": info,
        "weather_result": None
    })

if st.session_state["station_name"]:
    info = st.session_state.get("station_info", {})
    label = "主要観測所（全項目）" if info.get("type") == "major" else "アメダス（降水量のみ）"
    st.success(f"✅ 選択中：**{st.session_state['station_name']}**　{label}")

st.divider()

# 日付選択
st.subheader("📅 日付を選択")
col1, col2, col3 = st.columns(3)
cy = datetime.datetime.now().year
with col1: sel_year = st.selectbox("年", list(range(cy, cy - 3, -1)))
with col2: sel_month = st.selectbox("月", list(range(1, 13)), index=2)
with col3: sel_day = st.selectbox("日", list(range(1, 32)), index=0)
years_back = st.slider("集計年数（過去何年分）", min_value=5, max_value=15, value=10)
st.divider()

# 集計ボタン
if st.button("🔍 気象データを集計する", type="primary", use_container_width=True):
    if not st.session_state.get("station_name"):
        st.warning("地図をクリックして地点を選択してください。")
    else:
        station_name = st.session_state["station_name"]
        station_info = st.session_state["station_info"]
        prec_no = station_info.get("prec_no")
        block_no = station_info.get("block_no")
        amedas_code = station_info.get("amedas_code")
        is_amedas = (not prec_no or not block_no) and amedas_code

        if is_amedas:
            st.info("アメダス観測所のため降水量のみ集計します。気温・風速は近くの主要観測所（濃い青●）で取得できます。")

        records = []
        progress = st.progress(0, text="データ取得中...")
        errors = []
        for i, yr in enumerate(range(sel_year - years_back, sel_year)):
            progress.progress((i+1)/years_back, text=f"{yr}年のデータを取得中...")
            if is_amedas:
                rec = fetch_amedas_daily(amedas_code, yr, sel_month, sel_day)
            else:
                rec = fetch_weather_for_year(prec_no, block_no, yr, sel_month, sel_day)
            records.append(rec)
            if rec is None:
                errors.append(yr)
        progress.empty()

        if errors:
            st.warning(f"取得できなかった年：{', '.join(map(str, errors))}")

        result = analyze_data(records)
        if result:
            st.session_state["weather_result"] = result
            st.session_state["target_date"] = f"{sel_month}月{sel_day}日"
            st.rerun()
        else:
            st.error("データを取得できませんでした。観測所や日付を変えてお試しください。")

# 結果表示
if st.session_state.get("weather_result"):
    result = st.session_state["weather_result"]
    station_name = st.session_state["station_name"]
    target_date = st.session_state["target_date"]
    st.subheader(f"📊 集計結果：{station_name} {target_date}（過去{result['n']}年分）")

    # ① 降雨
    with st.container(border=True):
        st.markdown("### ① 降雨")
        rain_label, rain_color = rain_risk_label(result["rain_days"], result["n"])
        st.markdown(f"**判定：** :{rain_color}[{rain_label}]")
        st.markdown("**📅 24時間降水量**")
        col1, col2, col3 = st.columns(3)
        col1.metric("雨だった日数", f"{result['rain_days']} / {result['n']}年")
        col2.metric("最大降水量", f"{result['precip_max']} mm" if result['precip_max'] else "―")
        col3.metric("雨の日の平均", f"{result['precip_avg_rain']} mm" if result['rain_days'] > 0 else "―")
        col1, col2, col3 = st.columns(3)
        col1.metric("雨なし (<1mm)", f"{result['rain_0']}回")
        col2.metric("小雨 (1〜10mm)", f"{result['rain_1_10']}回")
        col3.metric("大雨 (10mm以上)", f"{result['rain_10plus']}回")
        st.markdown("**🌧️ 最大1時間雨量**")
        col1, col2 = st.columns(2)
        col1.metric("最大値（過去最悪）", f"{result['rain_1h_max']} mm" if result['rain_1h_max'] else "―")
        col2.metric("平均値", f"{result['rain_1h_avg']} mm" if result['rain_1h_avg'] else "―")
        precip_buf = make_precip_chart(result)
        st.image(precip_buf, use_container_width=True)
        st.session_state["precip_buf"] = precip_buf

        with st.expander("📋 年別データを確認する"):
            rows_data = []
            for i, r in enumerate(result["records"]):
                yr = sel_year - years_back + i + 1 if st.session_state.get("sel_year") else cy - result["n"] + i + 1
                rows_data.append({
                    "年": str(yr),
                    "降水量(mm)": str(r["precip"]) if r["precip"] is not None else "―",
                    "最大1時間(mm)": str(r.get("rain_1h_max")) if r.get("rain_1h_max") is not None else "―",
                    "平均気温(℃)": str(r["temp_avg"]) if r["temp_avg"] is not None else "―",
                    "最高気温(℃)": str(r["temp_max"]) if r["temp_max"] is not None else "―",
                    "最低気温(℃)": str(r["temp_min"]) if r["temp_min"] is not None else "―",
                    "平均風速(m/s)": str(r["wind_avg"]) if r["wind_avg"] is not None else "―",
                    "最大風速(m/s)": str(r["wind_max"]) if r["wind_max"] is not None else "―",
                })
            st.dataframe(pd.DataFrame(rows_data).set_index("年"), use_container_width=True)
            if result["records"] and "_raw" in result["records"][0] and result["records"][0]["_raw"]:
                st.caption(f"生データ列（最初の年）: {result['records'][0]['_raw']}")

    # ② 気温（データがある場合のみ）
    if result["temp_max_mean"] is not None:
        with st.container(border=True):
            st.markdown("### ② 気温")
            col1, col2, col3 = st.columns(3)
            col1.metric("平均気温", f"{result['temp_avg_mean']} ℃" if result['temp_avg_mean'] else "—")
            col2.metric("最高気温（平均）", f"{result['temp_max_mean']} ℃")
            col3.metric("最低気温（平均）", f"{result['temp_min_mean']} ℃" if result['temp_min_mean'] else "—")

        with st.container(border=True):
            st.markdown("### ③ ばらつき（振れ幅）")
            col1, col2 = st.columns(2)
            col1.metric("最高気温の最大", f"{result['temp_max_max']} ℃" if result['temp_max_max'] else "—")
            col1.metric("最高気温の最小", f"{result['temp_max_min']} ℃" if result['temp_max_min'] else "—")
            col2.metric("最低気温の最大", f"{result['temp_min_max']} ℃" if result['temp_min_max'] else "—")
            col2.metric("最低気温の最小", f"{result['temp_min_min']} ℃" if result['temp_min_min'] else "—")
            temp_buf = make_temp_chart(result)
            if temp_buf:
                st.image(temp_buf, use_container_width=True)
                st.session_state["temp_buf"] = temp_buf

    # ④ 風（データがある場合のみ）
    if result["wind_max_max"] is not None:
        with st.container(border=True):
            st.markdown("### ④ 風")
            wind_label, wind_color = wind_risk_label(result["wind_max_max"])
            st.markdown(f"**テント判定：** :{wind_color}[{wind_label}]")
            col1, col2, col3 = st.columns(3)
            col1.metric("平均風速（平均）", f"{result['wind_avg_mean']} m/s" if result['wind_avg_mean'] else "—")
            col2.metric("最大風速（平均）", f"{result['wind_max_mean']} m/s" if result['wind_max_mean'] else "—")
            col3.metric("最大風速（最大値）", f"{result['wind_max_max']} m/s", help="過去の最悪ケース")
            wind_buf = make_wind_chart(result)
            if wind_buf:
                st.image(wind_buf, use_container_width=True)
                st.session_state["wind_buf"] = wind_buf

    st.divider()

    # PDF
    st.subheader("📥 PDFレポート")
    with st.spinner("PDFを生成中..."):
        pdf_bytes = create_pdf(
            station_name, target_date, result,
            st.session_state.get("precip_buf"),
            st.session_state.get("temp_buf"),
            st.session_state.get("wind_buf")
        )
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="📄 PDFをダウンロード",
        data=pdf_bytes,
        file_name=f"気象集計_{station_name}_{target_date}_{now_str}.pdf",
        mime="application/pdf",
        type="primary"
    )