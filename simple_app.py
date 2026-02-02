import os
import time
import json
import re
import datetime
import requests
import xml.etree.ElementTree as ET
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from notion_client import Client
import google.generativeai as genai
from graphviz import Digraph

# 為替取得用（インストールされていない場合のフォールバック付き）
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

# ==========================================
# 0. APIキー読み込み設定
# ==========================================
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
if "NOTION_API_KEY" in st.secrets:
    os.environ["NOTION_API_KEY"] = st.secrets["NOTION_API_KEY"]
if "NOTION_PAGE_ID" in st.secrets:
    os.environ["NOTION_PAGE_ID"] = st.secrets["NOTION_PAGE_ID"]
if "NOTION_DATABASE_ID" in st.secrets and "NOTION_PAGE_ID" not in os.environ:
    os.environ["NOTION_PAGE_ID"] = st.secrets["NOTION_DATABASE_ID"]

# --- 1. 設定 ---
load_dotenv()
st.set_page_config(
    page_title="RSJP Intelligence Hub", 
    page_icon="💠", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# APIキー取得
NOTION_KEY = os.getenv("NOTION_API_KEY")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

# --- 2. データ取得関数 ---
def get_ritsumeikan_news():
    """立命館関連ニュース取得 (RSS)"""
    url = "https://news.google.com/rss/search?q=立命館+大学+学園+附属&hl=ja&gl=JP&ceid=JP:ja"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            news_items = []
            for item in root.findall(".//item")[:10]:
                title = item.find("title").text
                link = item.find("link").text
                pubDate = item.find("pubDate").text
                try:
                    dt = datetime.datetime.strptime(pubDate, '%a, %d %b %Y %H:%M:%S %Z')
                    date_str = dt.strftime('%m/%d')
                except:
                    date_str = ""
                
                if " - " in title: title = title.split(" - ")[0]
                news_items.append({"title": title, "link": link, "date": date_str})
            return news_items
    except: return []
    return []

@st.cache_data(ttl=3600)
def get_exchange_rates():
    """yfinanceを使ってリアルタイム為替レートを取得"""
    usd_jpy = 150.00
    cad_jpy = 110.00
    
    if HAS_YFINANCE:
        try:
            ticker_usd = yf.Ticker("USDJPY=X")
            hist_usd = ticker_usd.history(period="1d")
            if not hist_usd.empty:
                usd_jpy = hist_usd['Close'].iloc[-1]
            
            ticker_cad = yf.Ticker("CADJPY=X")
            hist_cad = ticker_cad.history(period="1d")
            if not hist_cad.empty:
                cad_jpy = hist_cad['Close'].iloc[-1]
        except Exception:
            pass
            
    return round(usd_jpy, 2), round(cad_jpy, 2)

# --- 3. デザイン (Pro Dashboard CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&family=Noto+Sans+JP:wght@400;700&display=swap');
    
    .stApp {
        background: #f4f6f9;
        color: #1a237e;
        font-family: 'Noto Sans JP', sans-serif;
    }
    header, #MainMenu, footer {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }

    /* カラム共通 */
    [data-testid="column"] {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        border: 1px solid white;
        height: 100%;
    }

    /* --- ヘッダー --- */
    .saas-header {
        display: flex; justify-content: space-between; align-items: center;
        background: linear-gradient(135deg, #7f1118, #b7102e);
        padding: 20px 30px; border-radius: 16px; color: white;
        box-shadow: 0 8px 32px rgba(127, 17, 24, 0.25); margin-bottom: 15px;
    }
    .saas-logo { font-family: 'Montserrat', sans-serif; font-size: 1.6em; font-weight: 800; letter-spacing: 1px; }
    .saas-logo span { font-weight: 400; opacity: 0.8; margin-left: 8px; font-size: 0.8em; }
    .status-indicator { background: rgba(255,255,255,0.1); padding: 5px 12px; border-radius: 20px; font-size: 0.75em; }

    /* --- 右カラム: 情報パネル --- */
    .info-card {
        background: #263238; color: white;
        border-radius: 10px; padding: 15px; margin-bottom: 15px;
        font-family: 'Montserrat', sans-serif;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        border: 1px solid #37474f;
    }
    .card-label { color: #b0bec5; font-size: 0.7em; font-weight: 700; margin-bottom: 5px; text-transform: uppercase; }
    .card-main { font-size: 1.8em; font-weight: 700; line-height: 1.0; }
    .card-sub { font-size: 0.8em; color: #90a4ae; margin-top: 2px; }
    
    /* 天気行 */
    .weather-row {
        display: flex; justify-content: space-between; align-items: center;
        margin-top: 10px; border-top: 1px solid #455a64; padding-top: 8px; font-size: 0.9em;
    }

    /* --- ニュースバナー & リスト --- */
    .news-wrapper {
        border-radius: 10px; overflow: hidden;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        margin-bottom: 20px; border: 1px solid #e0e0e0; background: white;
    }
    .news-banner {
        background: linear-gradient(90deg, #1a237e, #3949ab);
        color: white; padding: 10px 15px; font-family: 'Montserrat', sans-serif;
        font-weight: 700; font-size: 0.9em; display: flex; align-items: center;
    }
    .news-banner span { margin-left: auto; font-size: 0.7em; opacity: 0.8; background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 4px; }
    
    .news-content { max-height: 300px; overflow-y: auto; padding: 0; }
    .news-item {
        display: block; padding: 10px 15px; border-bottom: 1px solid #f5f5f5;
        text-decoration: none; color: #333; font-size: 0.85em; transition: 0.2s; line-height: 1.4;
    }
    .news-item:hover { background: #fef1f2; color: #b7102e; padding-left: 18px; }
    .news-date { color: #999; font-size: 0.85em; margin-right: 8px; font-family: monospace; }

    /* --- チャットエリア --- */
    div[data-testid="stChatMessage"]:nth-of-type(odd) { flex-direction: row-reverse; text-align: right; }
    div[data-testid="stChatMessage"]:nth-of-type(odd) div[data-testid="stMarkdownContainer"] {
        background: linear-gradient(135deg, #e3f2fd, #bbdefb); color: #0d47a1;
        padding: 12px 20px; border-radius: 18px 18px 0 18px; text-align: left;
    }
    div[data-testid="stChatMessage"]:nth-of-type(even) div[data-testid="stMarkdownContainer"] {
        background: white; border: 1px solid #e0e0e0;
        padding: 15px 25px; border-radius: 18px 18px 18px 0; width: 100%;
    }
    .stChatMessage .stAvatar { display: none; }

    /* 入力欄 */
    .stChatInput { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); width: 50%; z-index: 1000; }
    .stChatInput textarea {
        border-radius: 28px !important; border: 1px solid #ddd !important;
        padding: 15px 25px !important; min-height: 60px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1) !important;
    }
    .stChatInput textarea:focus { border-color: #b7102e !important; }

    /* 履歴リンク */
    .history-link a {
        display: block; padding: 8px 12px; margin-bottom: 6px; color: #555;
        text-decoration: none; background: #f5f5f5; border-radius: 8px; font-size: 0.85em;
        border-left: 3px solid transparent; transition: 0.2s;
    }
    .history-link a:hover { background: white; color: #b7102e; border-left: 3px solid #b7102e; }

</style>
""", unsafe_allow_html=True)

# --- 4. クラス定義 ---
class FullNotionLoader:
    def __init__(self, api_key):
        self.notion = Client(auth=api_key)
        self.visited_ids = set()

    def load_recursive(self, start_id, progress_callback):
        self.visited_ids = set()
        full_text = ""
        queue = [start_id]
        count = 0
        while queue:
            current_id = queue.pop(0)
            if current_id in self.visited_ids: continue
            self.visited_ids.add(current_id)
            page_text, child_ids = self._read_page_detailed(current_id)
            if page_text:
                full_text += page_text
                count += 1
                progress_callback(f"Syncing... {count} pages")
            queue.extend(child_ids)
            time.sleep(0.1) 
        return full_text, count

    def _read_page_detailed(self, page_id):
        text_part = ""
        child_ids = []
        try:
            try:
                page = self.notion.pages.retrieve(page_id)
                title = "Untitled"
                if "properties" in page:
                    for prop in page["properties"].values():
                        if prop["type"] == "title" and prop["title"]:
                            title = prop["title"][0]["plain_text"]
                            break
                text_part += f"\n\n{'='*20}\n【ページ: {title}】\n"
            except: pass
            has_more = True
            cursor = None
            while has_more:
                try: blocks = self.notion.blocks.children.list(block_id=page_id, start_cursor=cursor)