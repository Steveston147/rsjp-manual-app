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
# 1. 環境設定とAPIキーの読み込み（最重要）
# ==========================================

# Streamlit CloudのSecretsからキーを読み込み、環境変数としてセットする
# これにより、os.getenv()を使うライブラリも正常に動作します
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

if "NOTION_API_KEY" in st.secrets:
    os.environ["NOTION_API_KEY"] = st.secrets["NOTION_API_KEY"]

if "NOTION_DATABASE_ID" in st.secrets:
    os.environ["NOTION_DATABASE_ID"] = st.secrets["NOTION_DATABASE_ID"]

# ローカル環境（Antigravity）用の.env読み込み（クラウドでは無視されます）
load_dotenv()

# APIキーの取得確認
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Geminiの設定
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    st.error("Google API Keyが見つかりません。Secretsの設定を確認してください。")

# Notionクライアントの初期化
notion = None
if NOTION_API_KEY:
    notion = Client(auth=NOTION_API_KEY)

# ==========================================
# 2. ユーティリティ関数（時刻・整形など）
# ==========================================

# 日本時間 (JST) と バンクーバー時間 (PST) の定義
JST = datetime.timezone(datetime.timedelta(hours=9))
PST = datetime.timezone(datetime.timedelta(hours=-8)) # 冬時間

def get_current_time(tz):
    """指定したタイムゾーンの現在時刻をHH:MM形式で返す"""
    return datetime.datetime.now(tz).strftime("%H:%M")

def get_current_date(tz):
    """指定したタイムゾーンの現在日付をYYYY/MM/DD形式で返す"""
    return datetime.datetime.now(tz).strftime("%Y/%m/%d")

def wrap_text(text, width=15):
    """長いテキストを指定した文字数で改行する（図形のはみ出し防止用）"""
    return textwrap.fill(text, width=width)

# ==========================================
# 3. Notion検索機能
# ==========================================
def search_notion(query):
    """Notionデータベースを検索して関連情報を返す"""
    if not notion or not NOTION_DATABASE_ID:
        return "Notion APIキーまたはデータベースIDが設定されていません。"
    
    try:
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "Name", # ※実際のプロパティ名に合わせて調整が必要かもしれません
                "title": {
                    "contains": query
                }
            }
        )
        results = []
        for page in response.get("results", []):
            # ページ内のテキストを簡易的に取得（実際は詳細なブロック取得が必要な場合あり）
            props = page.get("properties", {})
            title_list = props.get("Name", {}).get("title", [])
            if title_list:
                results.append(title_list[0].get("plain_text", ""))
        
        if not results:
            return "Notionに関連情報が見つかりませんでした。"
        return "\n".join(results)
    except Exception as e:
        return f"Notion検索エラー: {e}"

# ==========================================
# 4. Gemini回答生成
# ==========================================
def get_gemini_response(user_input):
    """Notionの情報とGeminiの知識を組み合わせて回答する"""
    # まずNotionを検索（文脈として使用）
    notion_context = search_notion(user_input)
    
    prompt = f"""
    あなたはRitsumeikan RSJPプログラムの有能なアシスタントです。
    以下のNotionからの情報を参考に、ユーザーの質問に日本語で的確に答えてください。
    
    【Notionからの情報】
    {notion_context}
    
    【ユーザーの質問】
    {user_input}
    
    回答には、必要に応じて図解の提案を含めてください。
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp') # または gemini-pro
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

# ==========================================
# 5. アプリケーションUI (Streamlit)
# ==========================================

st.set_page_config(page_title="RSJP Intelligence Hub", layout="wide")

# CSSスタイルの適用（カードデザインなど）
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        margin-bottom: 5px;
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

# --- メインエリア ---
# ヘッダー
st.markdown("""
<div style='background-color:#A80025; padding:20px; border-radius:10px; color:white; margin-bottom:20px;'>
    <h2>💠 RSJP INTELLIGENCE HUB <span style='float:right; font-size:12px; background:#C94458; padding:5px 10px; border-radius:15px;'>● ONLINE</span></h2>
</div>
""", unsafe_allow_html=True)

# ダッシュボード (天気・時計)
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class='metric-card'>
        <div style='font-size:12px; color:#aaa;'>KYOTO HQ</div>
        <div style='font-size:32px; font-weight:bold; color:#FF4B4B;'>{get_current_time(JST)}</div>
        <div style='font-size:12px;'>{get_current_date(JST)}</div>
        <div style='margin-top:10px;'>⛅ Clear 12°C / 4°C</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='metric-card'>
        <div style='font-size:12px; color:#aaa;'>VANCOUVER</div>
        <div style='font-size:32px; font-weight:bold; color:#33ADFF;'>{get_current_time(PST)}</div>
        <div style='font-size:12px;'>{get_current_date(PST)}</div>
        <div style='margin-top:10px;'>🌧️ Rain 8°C / 5°C</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class='metric-card'>
        <div style='font-size:12px; color:#aaa;'>RATES (JPY)</div>
        <div style='font-size:24px; margin-top:10px;'>USD <b>148.52</b></div>
        <div style='font-size:24px;'>CAD <b>109.15</b></div>
    </div>
    """, unsafe_allow_html=True)

# ニュースフィードなど
st.info("📰 **RITS NEWS**: エデュケーション・ニュージーランドと「教育における協力協定」を締結")

# チャット入力
user_input = st.chat_input("質問を入力してください...")

if user_input:
    # ユーザーの質問を表示
    with st.chat_message("user"):
        st.write(user_input)
    
    # Geminiからの回答を取得
    response_text = get_gemini_response(user_input)
    
    # AIの回答を表示
    with st.chat_message("assistant"):
        st.write(response_text)
        
        # ユーザーの質問がRSJPの概要に関する場合、フローチャートを表示するロジック
        if "RSJP" in user_input and ("とは" in user_input or "概要" in user_input or "何" in user_input):
            st.subheader("手順・概要図")
            
            # Graphvizでフローチャート作成（★修正点：wrap_textで自動改行）
            dot = Digraph()
            dot.attr(rankdir='TB', size='8,5')
            dot.attr('node', shape='box', style='filled', fillcolor='#E0F7FA', fontname='IPAGothic')
            
            # ノード定義（長い文章は wrap_text で折り返す）
            dot.node('Start', 'RSJPとは？', fillcolor='#4DD0E1')
            dot.node('Title', wrap_text('Ritsumeikan Summer Japanese Program\n(立命館サマージャパニーズプログラム)', 20))
            
            dot.node('Purpose', wrap_text('目的:\n日本語学習と日本文化体験を通じた日本への理解深化', 15))
            dot.node('Content', wrap_text('内容:\n午前：日本語学習\n午後：日本文化講義・フィールドワーク', 15))
            
            dot.node('Target', wrap_text('対象:\n海外の現役大学生・大学院生\n(※在籍証明が必須)', 15))
            dot.node('Feature', wrap_text('特徴:\n立命館大学生によるバディサポート', 15))
            
            dot.node('Ops', wrap_text('運営:\n立命館大学 国際教育センター\n＋クレオテック(業務委託)', 15))
            
            # エッジ定義（つなぎ方）
            dot.edge('Start', 'Title')
            dot.edge('Title', 'Purpose')
            dot.edge('Title', 'Content')
            dot.edge('Purpose', 'Target')
            dot.edge('Content', 'Feature')
            dot.edge('Feature', 'Ops')
            
            st.graphviz_chart(dot)