import os
import time
import json
import re
import datetime
import requests
import xml.etree.ElementTree as ET
import streamlit as st
from dotenv import load_dotenv
from notion_client import Client
import google.generativeai as genai
from graphviz import Digraph

# --- 1. 設定 ---
load_dotenv()
st.set_page_config(
    page_title="RSJP Intelligence Hub", 
    page_icon="💠", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# APIキー
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
    .block-container { padding-top: 2rem; padding-bottom: 150px; }

    /* カラム共通 */
    [data-testid="column"] {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        border: 1px solid white;
    }

    /* --- ヘッダー (Ritsumeikan Engine Color) --- */
    .saas-header {
        display: flex; justify-content: space-between; align-items: center;
        background: linear-gradient(135deg, #7f1118, #b7102e);
        padding: 20px 30px; border-radius: 16px; color: white;
        box-shadow: 0 8px 32px rgba(127, 17, 24, 0.25); margin-bottom: 30px;
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
                except: break
                for block in blocks["results"]:
                    b_type = block["type"]
                    content = ""
                    if "rich_text" in block.get(b_type, {}):
                        content = "".join([t["plain_text"] for t in block[b_type]["rich_text"]])
                    if b_type == "paragraph": text_part += content + "\n"
                    elif "heading" in b_type: text_part += f"\n■{content}\n"
                    elif "list_item" in b_type: text_part += f"・{content}\n"
                    elif b_type == "callout": text_part += f"💡{content}\n"
                    elif b_type == "image":
                        caption = ""
                        if "caption" in block["image"] and block["image"]["caption"]:
                            caption = "".join([t["plain_text"] for t in block["image"]["caption"]])
                        text_part += f"\n[画像あり: {caption}]\n"
                    elif b_type == "table":
                        text_part += "\n【以下の表データあり】\n"
                        try:
                            rows = self.notion.blocks.children.list(block_id=block["id"])
                            for row in rows["results"]:
                                if "table_row" in row:
                                    cells = [ "".join([t["plain_text"] for t in cell]) for cell in row["table_row"]["cells"]]
                                    text_part += " | ".join(cells) + "\n"
                        except: text_part += "(表の読み込みに失敗)\n"
                    if b_type == "child_page":
                        child_ids.append(block["id"])
                        text_part += f"[リンク: {block['child_page']['title']}]\n"
                    elif b_type == "child_database":
                        try:
                            db_query = self.notion.databases.query(database_id=block["id"])
                            for row in db_query["results"]: child_ids.append(row["id"])
                        except: pass
                has_more = blocks.get("has_more", False)
                cursor = blocks.get("next_cursor")
        except Exception: pass
        return text_part, child_ids

def extract_data_safe(text):
    try:
        match = re.search(r"```json(.*?)```", text, re.DOTALL)
        json_str = match.group(1) if match else text
        start = json_str.find('{')
        end = json_str.rfind('}') + 1
        if start != -1 and end != 0:
            return json.loads(json_str[start:end])
    except: pass
    try:
        text_match = re.search(r'"text_explanation"\s*:\s*"(.*?)"(?:\s*,\s*"chart_code"|\s*,\s*"related_questions")', text, re.DOTALL)
        chart_match = re.search(r'"chart_code"\s*:\s*"(.*?)"(?:\s*,\s*"related_questions"|\s*\})', text, re.DOTALL)
        questions_match = re.search(r'"related_questions"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        extracted_text = text
        extracted_chart = None
        extracted_questions = []
        if text_match: extracted_text = text_match.group(1).replace('\\n', '\n').replace('\\"', '"')
        if chart_match: extracted_chart = chart_match.group(1).replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t')
        if questions_match:
            try: extracted_questions = [q.strip().replace('"', '') for q in questions_match.group(1).split(',')]
            except: pass
        return {"text_explanation": extracted_text, "chart_code": extracted_chart, "related_questions": extracted_questions}
    except:
        clean_text = re.sub(r'["{}]', '', text).replace("text_explanation:", "").replace("chart_code:", "")
        return {"text_explanation": clean_text, "chart_code": None, "related_questions": []}

# --- 5. アプリ本体 ---
def main():
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "prompt_trigger" not in st.session_state: st.session_state.prompt_trigger = None
    if "memo" not in st.session_state: st.session_state.memo = ""

    col_left, col_center, col_right = st.columns([1, 3, 1], gap="medium")

    # ========= 左カラム =========
    with col_left:
        st.markdown("### 💠 SHORTCUTS")
        presets = ["✈️ 海外旅行保険", "💴 経費精算フロー", "📞 緊急連絡網", "🥁 和太鼓手配", "🛂 ビザ申請"]
        for p in presets:
            if st.button(p, key=p, use_container_width=True):
                # ★修正: ボタンを押したらtriggerをセットしてrerun (ここはこのままでOK)
                st.session_state.prompt_trigger = p.split(" ", 1)[1] if " " in p else p
                st.rerun()

        st.divider()
        st.markdown("### 🕒 HISTORY")
        if st.session_state.chat_history:
            for i, msg in enumerate(st.session_state.chat_history):
                if msg["role"] == "user":
                    label = (msg["content"][:9] + "..") if len(msg["content"]) > 9 else msg["content"]
                    st.markdown(f"<div class='history-link'><a href='#msg-{i}'>📄 {label}</a></div>", unsafe_allow_html=True)
        else: st.caption("No History")
        
        st.divider()
        st.markdown("### 📌 MEMO")
        st.text_area("Sticky Note", value=st.session_state.memo, height=100, key="memo", placeholder="一時メモ...")

        st.divider()
        if "manual_text" not in st.session_state:
            if st.button("🔄 同期開始", type="primary", use_container_width=True):
                loader = FullNotionLoader(NOTION_KEY)
                with st.status("Fetching Data..."):
                    all_text, count = loader.load_recursive(NOTION_PAGE_ID, lambda msg: st.write(msg))
                st.session_state.manual_text = all_text
                st.rerun()

    # ========= 右カラム =========
    with col_right:
        now_jp = datetime.datetime.now()
        now_van = now_jp - datetime.timedelta(hours=17)

        st.markdown(f"""
        <div class="info-card" style="border-top: 3px solid #b7102e;">
            <div class="card-label">KYOTO HQ</div>
            <div class="card-main" style="color:#e91e63">{now_jp.strftime('%H:%M')}</div>
            <div class="card-sub">{now_jp.strftime('%Y/%m/%d')}</div>
            <div class="weather-row">
                <span>⛅ Clear</span>
                <span><b>12°C</b> / 4°C</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="info-card" style="border-top: 3px solid #03a9f4;">
            <div class="card-label">VANCOUVER</div>
            <div class="card-main" style="color:#40c4ff">{now_van.strftime('%H:%M')}</div>
            <div class="card-sub">{now_van.strftime('%Y/%m/%d')}</div>
            <div class="weather-row">
                <span>🌧️ Rain</span>
                <span><b>8°C</b> / 5°C</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="info-card" style="border-top: 3px solid #ffb300;">
            <div class="card-label">RATES (JPY)</div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <div><span style="color:#ccc; font-size:0.8em;">USD</span> <span style="font-weight:bold; font-size:1.2em;">148.52</span></div>
                <div><span style="color:#ccc; font-size:0.8em;">CAD</span> <span style="font-weight:bold; font-size:1.2em;">109.15</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="news-wrapper">
            <div class="news-banner">
                📰 RITS NEWS <span>RSS FEED</span>
            </div>
            <div class="news-content">
        """, unsafe_allow_html=True)
        
        news_items = get_ritsumeikan_news()
        if news_items:
            for item in news_items:
                st.markdown(f"""
                <a href="{item['link']}" target="_blank" class="news-item">
                    <span class="news-date">{item['date']}</span> {item['title']}
                </a>
                """, unsafe_allow_html=True)
        else:
            st.markdown("<div style='padding:15px; font-size:0.8em; color:#999;'>No updates</div>", unsafe_allow_html=True)
        
        st.markdown("</div></div>", unsafe_allow_html=True)

    # ========= 中央カラム =========
    with col_center:
        st.markdown("""
        <div class="saas-header">
            <div class="saas-logo">💠 RSJP <span>INTELLIGENCE HUB</span></div>
            <div class="status-indicator">● ONLINE</div>
        </div>
        """, unsafe_allow_html=True)
        
        if "manual_text" not in st.session_state:
            st.info("👈 左メニューで同期を開始してください")
        else:
            for i, msg in enumerate(st.session_state.chat_history):
                st.markdown(f"<div id='msg-{i}' style='margin-top:-60px; padding-top:60px;'></div>", unsafe_allow_html=True)
                with st.chat_message(msg["role"]):
                    if msg["type"] == "text": st.markdown(msg["content"])
                    elif msg["type"] == "chart": 
                        try: st.graphviz_chart(msg["content"])
                        except: pass
                    elif msg["type"] == "suggestions":
                        st.markdown("**💡 Next Actions:**")
                        cols = st.columns(len(msg["content"]))
                        for idx, q in enumerate(msg["content"]):
                            with cols[idx]:
                                if st.button(q, key=f"sug_{i}_{idx}"):
                                    st.session_state.prompt_trigger = q
                                    st.rerun()

            # 入力処理
            # 1. ユーザー入力の取得（テキスト入力またはトリガー）
            trigger_input = st.session_state.prompt_trigger
            
            # トリガーがある場合はそれを優先して処理開始フラグを立てる
            if trigger_input:
                user_input = trigger_input
                st.session_state.prompt_trigger = None # トリガー消費
            else:
                # トリガーがない場合は通常のチャット入力
                user_input = st.chat_input("質問を入力してください...")

            # 2. 入力があれば処理実行
            if user_input:
                with st.chat_message("user"):
                    st.markdown(user_input)
                st.session_state.chat_history.append({"role": "user", "type": "text", "content": user_input})

                genai.configure(api_key=GOOGLE_KEY)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                full_prompt = f"""
                あなたはRSJP（立命館大学 留学サポートデスク）の業務マニュアルAIです。
                明るく丁寧なトーンで回答してください。

                【回答ルール】
                1. **結論**: 端的に。
                2. **手順**: 詳細に。
                3. **⚠️ アドバイス**: 初心者が間違いやすい点を優しく先回りして教える。
                4. **Graphvizフローチャート**: 
                   - レイアウト: 縦型(`rankdir="TB"`)
                   - スタイル: 透明感 (bgcolor="transparent")
                   - **重要: ノード内の文字が長い場合は、必ず適宜 `\\n` で改行を入れること。**
                5. **関連情報**: 3つ提案。

                【JSON形式】
                ```json
                {{
                    "text_explanation": "マークダウンテキスト",
                    "chart_code": "DOT言語コード",
                    "related_questions": ["Q1", "Q2", "Q3"]
                }}
                ```
                【質問】{user_input}
                【マニュアル】{st.session_state.manual_text}
                """

                with st.chat_message("assistant"):
                    with st.spinner("AI Thinking..."):
                        try:
                            response = model.generate_content(full_prompt)
                            data = extract_data_safe(response.text)
                            
                            txt = data.get("text_explanation", response.text)
                            if txt.strip().startswith("{"): txt = txt.replace('"', '').replace('{', '').replace('}', '')
                            st.markdown(txt)
                            st.session_state.chat_history.append({"role": "assistant", "type": "text", "content": txt})

                            chart = data.get("chart_code")
                            if chart and "digraph" in chart:
                                glass_style = 'graph [bgcolor="transparent", fontcolor="#0d47a1", ranksep=0.6]; node [color="#2196f3", fontcolor="#0d47a1", style="filled,rounded", fillcolor="#e3f2fd", fixedsize=false, width=0, height=0, margin="0.2,0.1"]; edge [color="#2196f3"];'
                                chart = chart.replace('digraph {', f'digraph {{ {glass_style}')
                                chart = chart.replace('digraph G {', f'digraph G {{ {glass_style}')
                                
                                st.markdown("---")
                                st.caption("📊 Flowchart")
                                st.graphviz_chart(chart)
                                st.session_state.chat_history.append({"role": "assistant", "type": "chart", "content": chart})

                            sug = data.get("related_questions", [])
                            if sug:
                                st.session_state.chat_history.append({"role": "assistant", "type": "suggestions", "content": sug})
                                # ★重要: 最後のrerunは、サジェストボタンを表示させるために必要だが
                                # 直前の処理でrerunループしないように、user_inputの処理は完了している必要がある
                                st.rerun()
                        
                        except Exception as e:
                            st.error(f"Error: {e}")

if __name__ == "__main__":
    main()