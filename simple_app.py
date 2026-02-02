import time
import json
import re
import datetime
import requests
import xml.etree.ElementTree as ET
import streamlit as st
import os
import textwrap
from graphviz import Digraph
from dotenv import load_dotenv
from notion_client import Client
import google.generativeai as genai

# ==========================================
# 1. 環境設定とAPIキーの読み込み
# ==========================================

# Streamlit CloudのSecretsからキーを読み込み
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

if "NOTION_API_KEY" in st.secrets:
    os.environ["NOTION_API_KEY"] = st.secrets["NOTION_API_KEY"]

if "NOTION_DATABASE_ID" in st.secrets:
    os.environ["NOTION_DATABASE_ID"] = st.secrets["NOTION_DATABASE_ID"]

# ローカル環境用（.env）
load_dotenv()

# 変数セット
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Gemini初期化
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Notion初期化
notion = None
if NOTION_API_KEY:
    notion = Client(auth=NOTION_API_KEY)

# ==========================================
# 2. ユーティリティ関数
# ==========================================

JST = datetime.timezone(datetime.timedelta(hours=9))
PST = datetime.timezone(datetime.timedelta(hours=-8)) 

def get_current_time(tz):
    return datetime.datetime.now(tz).strftime("%H:%M")

def get_current_date(tz):
    return datetime.datetime.now(tz).strftime("%Y/%m/%d")

def wrap_text(text, width=15):
    """長いテキストを改行する（図形のはみ出し防止）"""
    return textwrap.fill(text, width=width)

# ==========================================
# 3. Notion検索機能
# ==========================================
def search_notion(query):
    if not notion or not NOTION_DATABASE_ID:
        return "" # エラー時は空文字を返してGeminiの知識だけで回答させる
    
    try:
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={"property": "Name", "title": {"contains": query}}
        )
        results = []
        for page in response.get("results", []):
            props = page.get("properties", {})
            title_list = props.get("Name", {}).get("title", [])
            if title_list:
                results.append(title_list[0].get("plain_text", ""))
        return "\n".join(results)
    except:
        return ""

# ==========================================
# 4. Gemini回答生成
# ==========================================
def get_gemini_response(user_input):
    notion_context = search_notion(user_input)
    
    prompt = f"""
    あなたはRitsumeikan RSJPプログラムの有能なアシスタントです。
    ユーザーの質問に日本語で的確に答えてください。
    
    【Notion情報（参考）】
    {notion_context}
    
    【質問】
    {user_input}
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"エラー: {str(e)}"

# ==========================================
# 5. UI構築（ここを元のレイアウトに戻しました）
# ==========================================

st.set_page_config(page_title="RSJP Intelligence Hub", layout="wide")

# CSS: カードのデザイン定義
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px; /* カード間の隙間 */
        border-left: 5px solid #A80025; /* 左側のアクセントライン */
    }
    .stChatInput {
        position: fixed;
        bottom: 30px;
    }
</style>
""", unsafe_allow_html=True)

# --- サイドバー ---
with st.sidebar:
    st.header("💠 SHORTCUTS")
    st.button("✈️ 海外旅行保険")
    st.button("💴 経費精算フロー")
    st.button("📞 緊急連絡網")
    st.button("🥁 和太鼓手配")
    st.button("📝 ビザ申請")
    st.markdown("---")
    st.header("🕒 HISTORY")
    st.text("No History")
    st.markdown("---")
    st.header("📌 MEMO")
    st.text_area("Sticky Note", placeholder="一時メモ...")

# --- ヘッダー ---
st.markdown("""
<div style='background-color:#A80025; padding:20px; border-radius:10px; color:white; margin-bottom:20px;'>
    <h2>💠 RSJP INTELLIGENCE HUB <span style='float:right; font-size:12px; background:#C94458; padding:5px 10px; border-radius:15px;'>● ONLINE</span></h2>
</div>
""", unsafe_allow_html=True)

# --- レイアウト分割（左：チャット / 右：情報パネル） ---
col_main, col_info = st.columns([0.7, 0.3]) # 7:3の比率で分割

# ▼▼▼ 右カラム：情報パネル（時計などを縦に並べる） ▼▼▼
with col_info:
    # 1. 京都カード
    st.markdown(f"""
    <div class='metric-card'>
        <div style='font-size:12px; color:#aaa;'>KYOTO HQ</div>
        <div style='font-size:36px; font-weight:bold; color:#FF4B4B;'>{get_current_time(JST)}</div>
        <div style='font-size:14px;'>{get_current_date(JST)}</div>
        <div style='margin-top:5px;'>⛅ Clear 12°C / 4°C</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. バンクーバーカード
    st.markdown(f"""
    <div class='metric-card' style='border-left: 5px solid #33ADFF;'>
        <div style='font-size:12px; color:#aaa;'>VANCOUVER</div>
        <div style='font-size:36px; font-weight:bold; color:#33ADFF;'>{get_current_time(PST)}</div>
        <div style='font-size:14px;'>{get_current_date(PST)}</div>
        <div style='margin-top:5px;'>🌧️ Rain 8°C / 5°C</div>
    </div>
    """, unsafe_allow_html=True)

    # 3. 為替カード
    st.markdown("""
    <div class='metric-card' style='border-left: 5px solid #FFD700;'>
        <div style='font-size:12px; color:#aaa;'>RATES (JPY)</div>
        <div style='font-size:20px; margin-top:5px;'>USD <b>148.52</b></div>
        <div style='font-size:20px;'>CAD <b>109.15</b></div>
    </div>
    """, unsafe_allow_html=True)
    
    # 4. ニュース
    st.info("📰 **RITS NEWS**\nエデュケーション・ニュージーランドと協定締結")

# ▼▼▼ 左カラム：チャットエリア ▼▼▼
with col_main:
    st.write("何かお手伝いしましょうか？")
    
    # チャット入力
    user_input = st.chat_input("質問を入力してください...")

    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        
        response_text = get_gemini_response(user_input)
        
        with st.chat_message("assistant"):
            st.write(response_text)
            
            # 図解ロジック（自動改行機能付き）
            if "RSJP" in user_input and ("とは" in user_input or "概要" in user_input):
                st.subheader("概要図")
                dot = Digraph()
                dot.attr(rankdir='TB')
                dot.attr('node', shape='box', style='filled', fillcolor='#E0F7FA', fontname='IPAGothic')
                
                # wrap_textを使って文字が枠からはみ出ないようにする
                dot.node('Start', 'RSJPとは？', fillcolor='#4DD0E1')
                dot.node('Title', wrap_text('Ritsumeikan Summer Japanese Program (立命館サマージャパニーズプログラム)', 20))
                dot.node('Purpose', wrap_text('目的:\n日本語学習と日本文化体験を通じた日本への理解深化', 15))
                dot.node('Content', wrap_text('内容:\n午前：日本語学習\n午後：日本文化講義・フィールドワーク', 15))
                dot.node('Target', wrap_text('対象:\n海外の現役大学生・大学院生 (※在籍証明が必須)', 15))
                dot.node('Feature', wrap_text('特徴:\n立命館大学生によるバディサポート', 15))
                dot.node('Ops', wrap_text('運営:\n立命館大学 国際教育センター＋クレオテック', 15))
                
                dot.edge('Start', 'Title')
                dot.edge('Title', 'Purpose')
                dot.edge('Title', 'Content')
                dot.edge('Purpose', 'Target')
                dot.edge('Content', 'Feature')
                dot.edge('Feature', 'Ops')
                
                st.graphviz_chart(dot)