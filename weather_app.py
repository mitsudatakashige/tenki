import streamlit as st
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
import folium
from streamlit_folium import st_folium
import datetime
import io
import json
import math

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
FONT = "HeiseiKakuGo-W5"
import os
import urllib.request

# 日本語フォントをダウンロードして設定
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

# 主要気象観測所リスト（station_id, 名称, 都道府県, lat, lon）
STATIONS = [
    ("44132", "札幌", "北海道", 43.0595, 141.3386),
    ("32402", "青森", "青森県", 40.8244, 140.7694),
    ("33472", "盛岡", "岩手県", 39.6956, 141.1544),
    ("34392", "仙台", "宮城県", 38.2597, 140.8997),
    ("35139", "秋田", "秋田県", 39.7175, 140.0997),
    ("36127", "山形", "山形県", 38.2556, 140.3394),
    ("36361", "福島", "福島県", 37.7608, 140.4739),
    ("40201", "水戸", "茨城県", 36.3814, 140.4664),
    ("41277", "宇都宮", "栃木県", 36.5497, 139.8703),
    ("42251", "前橋", "群馬県", 36.3914, 139.0636),
    ("43267", "熊谷", "埼玉県", 36.1472, 139.3883),
    ("44136", "東京", "東京都", 35.6894, 139.6917),
    ("45147", "横浜", "神奈川県", 35.4478, 139.6425),
    ("50331", "新潟", "新潟県", 37.9161, 139.0364),
    ("50746", "富山", "富山県", 36.6953, 137.2114),
    ("51106", "金沢", "石川県", 36.5661, 136.6561),
    ("51261", "福井", "福井県", 36.0653, 136.2219),
    ("49142", "甲府", "山梨県", 35.6639, 138.5689),
    ("48156", "長野", "長野県", 36.6514, 138.1814),
    ("51076", "岐阜", "岐阜県", 35.3911, 136.7222),
    ("50976", "静岡", "静岡県", 34.9769, 138.3833),
    ("51106", "名古屋", "愛知県", 35.1667, 136.9667),
    ("54232", "津", "三重県", 34.7306, 136.5086),
    ("61286", "大津", "滋賀県", 35.0042, 135.8686),
    ("61286", "京都", "京都府", 35.0117, 135.7683),
    ("62078", "大阪", "大阪府", 34.6861, 135.5200),
    ("63518", "神戸", "兵庫県", 34.6939, 135.1950),
    ("65042", "奈良", "奈良県", 34.6853, 135.8328),
    ("65356", "和歌山", "和歌山県", 34.2261, 135.1675),
    ("69100", "鳥取", "鳥取県", 35.5036, 134.2378),
    ("68132", "松江", "島根県", 35.4681, 133.0506),
    ("67437", "岡山", "岡山県", 34.6619, 133.9350),
    ("67437", "広島", "広島県", 34.3853, 132.4553),
    ("71106", "山口", "山口県", 34.1861, 131.4711),
    ("72086", "徳島", "徳島県", 34.0658, 134.5594),
    ("72086", "高松", "香川県", 34.3400, 134.0436),
    ("73166", "松山", "愛媛県", 33.8394, 132.7656),
    ("74181", "高知", "高知県", 33.5597, 133.5311),
    ("82182", "福岡", "福岡県", 33.5903, 130.3608),
    ("85142", "佐賀", "佐賀県", 33.2642, 130.3006),
    ("84496", "長崎", "長崎県", 32.7503, 129.8775),
    ("86141", "熊本", "熊本県", 32.8031, 130.7006),
    ("87376", "大分", "大分県", 33.2381, 131.6067),
    ("88317", "宮崎", "宮崎県", 31.9111, 131.4239),
    ("88836", "鹿児島", "鹿児島県", 31.5606, 130.5578),
    ("91197", "那覇", "沖縄県", 26.2044, 127.6883),
]

def find_nearest_station(lat, lon):
    best = None
    best_dist = float("inf")
    for s in STATIONS:
        sid, name, pref, slat, slon = s
        d = math.sqrt((lat - slat)**2 + (lon - slon)**2)
        if d < best_dist:
            best_dist = d
            best = s
    return best

def fetch_weather_data(station_id, year, month, day):
    """気象庁過去データAPIから日別データを取得"""
    url = (
        f"https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php"
        f"?prec_no=82&block_no={station_id}&year={year}&month={month:02d}&day=1&view=p1"
    )
    # 気象庁の実際のAPIエンドポイント
    # daily観測データCSVを利用
    csv_url = (
        f"https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php"
        f"?prec_no=82&block_no={station_id}&year={year}&month={month}&day={day}&view=p1"
    )
    return None

def fetch_jma_daily(prec_no, block_no, year, month):
    """気象庁からCSVデータを取得"""
    url = f"https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php?prec_no={prec_no}&block_no={block_no}&year={year}&month={month}&view=p1"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        return r.text
    except:
        return None

# 気象庁の観測所マスタ（prec_no込み）
# 気象庁アメダスAPIから観測所リストを動的取得
@st.cache_data(ttl=86400)
def load_station_master():
    """気象庁APIから全国観測所リストを取得（主要観測所＋アメダス）"""
    stations = {}

    # ① 主要観測所（気圧・気温・風・降水すべてあり）
    try:
        r = requests.get(
            "https://www.data.jma.go.jp/obd/stats/etrn/select/prefecture00.php",
            timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    except:
        pass

    # 気象庁アメダス観測所JSON
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
            # アメダスはblock_noがないので別URL形式
            stations[name] = {
                "prec_no": None,
                "block_no": None,
                "amedas_code": code,
                "lat": lat,
                "lon": lon,
                "type": "amedas"
            }
    except Exception as e:
        pass

    # ② 主要観測所マスタ（確実にデータ取得できる）を上書き追加
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


def find_nearest_station_master(lat, lon, stations):
    best_name = None
    best_dist = float("inf")
    for name, info in stations.items():
        d = math.sqrt((lat - info["lat"])**2 + (lon - info["lon"])**2)
        if d < best_dist:
            best_dist = d
            best_name = name
    return best_name, stations[best_name]


def fetch_amedas_daily(amedas_code, year, month, day):
    """アメダスAPIから指定日の降水量を取得"""
    try:
        date_str = f"{year}{month:02d}{day:02d}"
        # 3時間ごとのデータファイルを取得（00,03,06,09,12,15,18,21時）
        total_precip = 0.0
        has_data = False
        for hour in ["000000", "030000", "060000", "090000", "120000", "150000", "180000", "210000"]:
            url = f"https://www.jma.go.jp/bosai/amedas/data/point/{amedas_code}/{date_str}_{hour}.json"
            try:
                r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code != 200:
                    continue
                data = r.json()
                # 各時刻の降水量を積算
                for time_key, vals in data.items():
                    if "precipitation1h" in vals:
                        p = vals["precipitation1h"]
                        if isinstance(p, list) and len(p) > 0:
                            try:
                                total_precip += float(p[0])
                                has_data = True
                            except:
                                pass
            except:
                continue
        if has_data:
            return {
                "precip": round(total_precip, 1),
                "rain_1h_max": None,
                "temp_avg": None,
                "temp_max": None,
                "temp_min": None,
                "wind_avg": None,
                "wind_max": None,
                "_raw": [],
            }
        return None
    except Exception as e:
        return None


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
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if not cols:
                continue
            try:
                row_day = int(cols[0].get_text(strip=True))
            except:
                continue
            if row_day == day:
                texts = [c.get_text(strip=True) for c in cols]
                def safe_float(s):
                    try:
                        s = str(s).replace("//", "").replace("]", "").replace("[", "")
                        s = s.replace("x", "").replace("#", "").replace("--", "")
                        s = s.replace(" ", "").replace("■", "").strip()
                        if s in ("", "-", "///", "×"): return None
                        return float(s)
                    except:
                        return None
                # 気象庁daily_s1 実際の列順（主要観測所）:
                # 0:日 1:気圧(現地) 2:気圧(海面) 3:降水量合計
                # 4:最大1時間降水量 5:最大10分間降水量
                # 6:平均気温 7:最高気温 8:最低気温
                # 9:湿度(平均) 10:蒸気圧 11:平均風速 12:最大風速 13:最大風向
                return {
                    "precip": safe_float(texts[3]) if len(texts) > 3 else None,
                    "rain_1h_max": safe_float(texts[4]) if len(texts) > 4 else None,
                    "temp_avg": safe_float(texts[6]) if len(texts) > 6 else None,
                    "temp_max": safe_float(texts[7]) if len(texts) > 7 else None,
                    "temp_min": safe_float(texts[8]) if len(texts) > 8 else None,
                    "wind_avg": safe_float(texts[11]) if len(texts) > 11 else None,
                    "wind_max": safe_float(texts[12]) if len(texts) > 12 else None,
                    "_raw": texts,
                }
        return None
    except Exception as e:
        return None


def analyze_data(records):
    valid = [r for r in records if r]
    n = len(valid)
    if n == 0:
        return None

    # 降雨（24時間合計）
    precips = [(r["precip"] if r["precip"] is not None else 0.0) for r in valid]
    rain_days = sum(1 for p in precips if p >= 1.0)
    rain_0 = sum(1 for p in precips if p < 1.0)
    rain_1_10 = sum(1 for p in precips if 1.0 <= p < 10.0)
    rain_10plus = sum(1 for p in precips if p >= 10.0)
    precip_max = round(max(precips), 1) if precips else None
    precip_avg_rain = round(sum(p for p in precips if p >= 1.0) / max(sum(1 for p in precips if p >= 1.0), 1), 1)

    # 1時間最大雨量
    rain_1h_list = [r["rain_1h_max"] for r in valid if r.get("rain_1h_max") is not None]

    # 気温
    temp_avgs = [r["temp_avg"] for r in valid if r["temp_avg"] is not None]
    temp_maxs = [r["temp_max"] for r in valid if r["temp_max"] is not None]
    temp_mins = [r["temp_min"] for r in valid if r["temp_min"] is not None]

    # 風
    wind_avgs = [r["wind_avg"] for r in valid if r["wind_avg"] is not None]
    wind_maxs = [r["wind_max"] for r in valid if r["wind_max"] is not None]

    def avg(lst): return round(sum(lst)/len(lst), 1) if lst else None
    def mx(lst): return round(max(lst), 1) if lst else None
    def mn(lst): return round(min(lst), 1) if lst else None

    return {
        "n": n,
        "rain_days": rain_days,
        "rain_0": rain_0,
        "rain_1_10": rain_1_10,
        "rain_10plus": rain_10plus,
        "precip_n": len(precips),
        "precips": precips,
        "precip_max": precip_max,
        "precip_avg_rain": precip_avg_rain,
        "rain_1h_list": rain_1h_list,
        "rain_1h_max": mx(rain_1h_list),
        "rain_1h_avg": avg(rain_1h_list),
        "temp_avg_mean": avg(temp_avgs),
        "temp_max_mean": avg(temp_maxs),
        "temp_min_mean": avg(temp_mins),
        "temp_max_max": mx(temp_maxs),
        "temp_max_min": mn(temp_maxs),
        "temp_min_max": mx(temp_mins),
        "temp_min_min": mn(temp_mins),
        "wind_avg_mean": avg(wind_avgs),
        "wind_max_mean": avg(wind_maxs),
        "wind_max_max": mx(wind_maxs),
        "records": valid,
    }


def make_precip_chart(result):
    fig, ax = plt.subplots(figsize=(5, 3))
    labels = ["雨なし\n(<1mm)", "小雨\n(1〜10mm)", "大雨\n(10mm以上)"]
    vals = [result["rain_0"], result["rain_1_10"], result["rain_10plus"]]
    bar_colors = ["#90CAF9", "#42A5F5", "#1565C0"]
    bars = ax.bar(labels, vals, color=bar_colors, edgecolor="white", linewidth=1.5)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f"{val}回", ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax.set_ylabel("回数", fontsize=10)
    ax.set_title("降水量の分布", fontsize=12, fontweight="bold")
    ax.set_ylim(0, max(vals) * 1.3 + 1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

def make_temp_chart(result):
    records = result["records"]
    # None除外しつつインデックスも揃える
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
    current_year = datetime.datetime.now().year
    ax.set_xticklabels([str(current_year - len(records) + i + 1) for i in xs], fontsize=8)
    ax.set_ylabel("気温 (℃)", fontsize=10)
    ax.set_title("過去の気温推移", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8, loc="best")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

def make_wind_chart(result):
    records = result["records"]
    wind_avgs = [r["wind_avg"] for r in records if r["wind_avg"] is not None]
    wind_maxs = [r["wind_max"] for r in records if r["wind_max"] is not None]

    fig, ax = plt.subplots(figsize=(7, 4))
    xs = range(len(wind_maxs))
    ax.bar(xs, wind_maxs, color="#78909C", alpha=0.7, label="最大風速")
    ax.plot(xs, wind_avgs[:len(xs)], "o-", color="#E53935", label="平均風速", linewidth=2, zorder=5)
    ax.axhline(y=10, color="orange", linestyle="--", alpha=0.7, label="10m/s (テント注意)")
    ax.axhline(y=15, color="red", linestyle="--", alpha=0.7, label="15m/s (テント撤収)")
    ax.set_xticks(range(len(records)))
    current_year = datetime.datetime.now().year
    ax.set_xticklabels([str(current_year - len(records) + i + 1) for i in range(len(records))], fontsize=8)
    ax.set_ylabel("風速 (m/s)", fontsize=10)
    ax.set_title("過去の風速推移", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

def wind_risk_label(wind_max_max):
    if wind_max_max is None: return "不明", "gray"
    if wind_max_max >= 15: return "⚠️ 要注意（撤収検討）", "red"
    if wind_max_max >= 10: return "🔶 注意（ペグ増し）", "orange"
    return "✅ 概ね安全", "green"

def rain_risk_label(rain_days, n):
    if n == 0: return "不明", "gray"
    ratio = rain_days / n
    if ratio >= 0.5: return "☔ 雨の可能性が高い", "red"
    if ratio >= 0.3: return "🌂 雨の可能性あり", "orange"
    return "☀️ 概ね晴れ傾向", "green"

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
st.caption("地図をクリックして地点を選択し、日付を指定すると過去10年分の気象データを集計します。")
st.divider()

# 観測所リスト読み込み
with st.spinner("観測所データを読み込み中..."):
    STATION_MASTER = load_station_master()

# セッション初期化
if "clicked_lat" not in st.session_state:
    st.session_state["clicked_lat"] = None
if "clicked_lon" not in st.session_state:
    st.session_state["clicked_lon"] = None
if "station_name" not in st.session_state:
    st.session_state["station_name"] = None
if "weather_result" not in st.session_state:
    st.session_state["weather_result"] = None

# 地図
st.subheader("📍 地点を選択")
st.caption("地図をクリックすると最寄りの気象観測所が自動選択されます。")

m = folium.Map(location=[36.0, 137.0], zoom_start=5)
for name, info in STATION_MASTER.items():
    color = "#1565C0" if info.get("type") == "major" else "#90CAF9"
    folium.CircleMarker(
        location=[info["lat"], info["lon"]],
        radius=4 if info.get("type") == "major" else 3,
        color=color, fill=True, fill_opacity=0.6,
        tooltip=f"{name}（{'主要' if info.get('type') == 'major' else 'アメダス'}）"
    ).add_to(m)
if st.session_state["clicked_lat"]:
    folium.Marker(
        location=[st.session_state["clicked_lat"], st.session_state["clicked_lon"]],
        popup=f"選択地点\n最寄り観測所：{st.session_state['station_name']}",
        icon=folium.Icon(color="red", icon="home")
    ).add_to(m)

map_data = st_folium(m, width=700, height=400, returned_objects=["last_clicked"])

if map_data and map_data.get("last_clicked"):
    clat = map_data["last_clicked"]["lat"]
    clon = map_data["last_clicked"]["lng"]
    name, info = find_nearest_station_master(clat, clon, STATION_MASTER)
    st.session_state["clicked_lat"] = clat
    st.session_state["clicked_lon"] = clon
    st.session_state["station_name"] = name
    st.session_state["station_info"] = info
    st.session_state["weather_result"] = None

if st.session_state["station_name"]:
    st.success(f"✅ 選択中の観測所：**{st.session_state['station_name']}**")

st.divider()

# 日付選択
st.subheader("📅 日付を選択")
col1, col2, col3 = st.columns(3)
current_year = datetime.datetime.now().year
with col1:
    sel_year = st.selectbox("年", list(range(current_year, current_year - 3, -1)))
with col2:
    sel_month = st.selectbox("月", list(range(1, 13)), index=2)
with col3:
    sel_day = st.selectbox("日", list(range(1, 32)), index=0)

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
            st.info("アメダス観測所のため降水量のみ集計します。気温・風速は主要観測所（濃い青丸）で取得できます。")

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
            st.session_state["sel_year"] = sel_year
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
        with col1:
            st.metric("雨だった日数", f"{result['rain_days']} / {result['n']}年")
        with col2:
            st.metric("最大降水量", f"{result['precip_max']} mm" if result['precip_max'] else "―")
        with col3:
            st.metric("雨の日の平均降水量", f"{result['precip_avg_rain']} mm" if result['rain_days'] > 0 else "―")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("雨なし (<1mm)", f"{result['rain_0']}回")
        with col2:
            st.metric("小雨 (1〜10mm)", f"{result['rain_1_10']}回")
        with col3:
            st.metric("大雨 (10mm以上)", f"{result['rain_10plus']}回")

        st.markdown("**🌧️ 最大1時間雨量**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("最大1時間雨量（最大値）", f"{result['rain_1h_max']} mm" if result['rain_1h_max'] else "―", help="過去の最悪ケース")
        with col2:
            st.metric("最大1時間雨量（平均）", f"{result['rain_1h_avg']} mm" if result['rain_1h_avg'] else "―")
        precip_buf = make_precip_chart(result)
        st.image(precip_buf, use_container_width=True)
        st.session_state["precip_buf"] = precip_buf

        # 年別降水量テーブル（デバッグ兼確認用）
        with st.expander("📋 年別データを確認する"):
            current_year = datetime.datetime.now().year
            rows_data = []
            for i, r in enumerate(result["records"]):
                yr = current_year - result["n"] + i + 1
                rows_data.append({
                    "年": yr,
                    "降水量(mm)": r["precip"] if r["precip"] is not None else "―",
                    "最大1時間雨量(mm)": r.get("rain_1h_max") if r.get("rain_1h_max") is not None else "―",
                    "平均気温(℃)": r["temp_avg"] if r["temp_avg"] is not None else "―",
                    "最高気温(℃)": r["temp_max"] if r["temp_max"] is not None else "―",
                    "最低気温(℃)": r["temp_min"] if r["temp_min"] is not None else "―",
                    "平均風速(m/s)": r["wind_avg"] if r["wind_avg"] is not None else "―",
                    "最大風速(m/s)": r["wind_max"] if r["wind_max"] is not None else "―",
                })
            import pandas as _pd
            st.dataframe(_pd.DataFrame(rows_data).set_index("年"), use_container_width=True)
            # 生データ（列確認用）
            if result["records"] and "_raw" in result["records"][0]:
                st.caption(f"生データ列（最初の年）: {result['records'][0]['_raw']}")

    # ② 気温
    with st.container(border=True):
        st.markdown("### ② 気温")
        col1, col2, col3 = st.columns(3)
        col1.metric("平均気温", f"{result['temp_avg_mean']} ℃" if result['temp_avg_mean'] else "—")
        col2.metric("最高気温（平均）", f"{result['temp_max_mean']} ℃" if result['temp_max_mean'] else "—")
        col3.metric("最低気温（平均）", f"{result['temp_min_mean']} ℃" if result['temp_min_mean'] else "—")

    # ③ ばらつき
    with st.container(border=True):
        st.markdown("### ③ ばらつき（振れ幅）")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("最高気温の最大", f"{result['temp_max_max']} ℃" if result['temp_max_max'] else "—")
            st.metric("最高気温の最小", f"{result['temp_max_min']} ℃" if result['temp_max_min'] else "—")
        with col2:
            st.metric("最低気温の最大", f"{result['temp_min_max']} ℃" if result['temp_min_max'] else "—")
            st.metric("最低気温の最小", f"{result['temp_min_min']} ℃" if result['temp_min_min'] else "—")
        temp_buf = make_temp_chart(result)
        st.image(temp_buf, use_container_width=True)
        st.session_state["temp_buf"] = temp_buf

    # ④ 風
    with st.container(border=True):
        st.markdown("### ④ 風")
        wind_label, wind_color = wind_risk_label(result["wind_max_max"])
        st.markdown(f"**テント判定：** :{wind_color}[{wind_label}]")
        col1, col2, col3 = st.columns(3)
        col1.metric("平均風速（平均）", f"{result['wind_avg_mean']} m/s" if result['wind_avg_mean'] else "—")
        col2.metric("最大風速（平均）", f"{result['wind_max_mean']} m/s" if result['wind_max_mean'] else "—")
        col3.metric("最大風速（最大値）", f"{result['wind_max_max']} m/s" if result['wind_max_max'] else "—", help="過去の最悪ケース")
        wind_buf = make_wind_chart(result)
        st.image(wind_buf, use_container_width=True)
        st.session_state["wind_buf"] = wind_buf

    st.divider()

    # PDF生成
    st.subheader("📥 PDFレポート")
    precip_buf = st.session_state.get("precip_buf")
    temp_buf = st.session_state.get("temp_buf")
    wind_buf = st.session_state.get("wind_buf")
    with st.spinner("PDFを生成中..."):
        pdf_bytes = create_pdf(station_name, target_date, result, precip_buf, temp_buf, wind_buf)
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="📄 PDFをダウンロード",
        data=pdf_bytes,
        file_name=f"気象集計_{station_name}_{target_date}_{now_str}.pdf",
        mime="application/pdf",
        type="primary"
    )