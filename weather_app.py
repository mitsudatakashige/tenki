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
    """アメダスAPIから指定日の降水量を取得
    気象庁アメダスAPIは1時間ごとのJSONを提供:
    https://www.jma.go.jp/bosai/amedas/data/point/{code}/{YYYYMMDD_HH0000}.json
    各ファイルに過去1時間分のデータが入っている
    """
    try:
        date_str = f"{year}{month:02d}{day:02d}"
        total_precip = 0.0
        rain_1h_max = 0.0
        has_data = False

        # 1時間ごと 00時〜23時
        for hour in range(24):
            time_str = f"{hour:02d}0000"
            url = f"https://www.jma.go.jp/bosai/amedas/data/point/{amedas_code}/{date_str}_{time_str}.json"
            try:
                r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code != 200:
                    continue
                data = r.json()
                # JSONは {"YYYYMMDDHHMMSS": {"precipitation10m": [val, quality], ...}} の形式
                for time_key, vals in data.items():
                    # 1時間降水量
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