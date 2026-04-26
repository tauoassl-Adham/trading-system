import streamlit as st
import websocket
import json
import threading

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="Scylla Institutional Dashboard", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# 2. تنسيق CSS
st.markdown("""
    <style>
    .signal-box { border-radius: 10px; padding: 15px; margin-bottom: 10px; border-left: 5px solid #00ff00; background-color: #f0f2f6; color: black; }
    </style>
""", unsafe_allow_html=True)

# 3. نظام اللغات (مصحح)
if 'lang' not in st.session_state: st.session_state.lang = 'en'

def toggle_lang():
    st.session_state.lang = 'ar' if st.session_state.lang == 'en' else 'en'

texts = {
    'en': {'title': 'Scylla Trading System', 'chart': 'Live Market Feed', 'signals': 'Trade Signals', 'lang_btn': 'Switch to Arabic 🇦🇷'},
    'ar': {'title': 'نظام Scylla للتداول', 'chart': 'مراقبة السوق', 'signals': 'إشارات التداول', 'lang_btn': 'التبديل للإنجليزية 🇬🇧'}
}

# 4. محرك استقبال البيانات
if 'last_signal' not in st.session_state: st.session_state.last_signal = None

def on_message(ws, message):
    try:
        # طباعة البيانات الخام في التيرمنال لنرى ماذا يصل فعلياً
        print(f"DEBUG: Received message: {message}") 
        data = json.loads(message)
        st.session_state.last_signal = data
    except Exception as e:
        print(f"DEBUG: Error parsing: {e}")

from streamlit.runtime.scriptrunner import add_script_run_ctx

def run_ws():
    ws = websocket.WebSocketApp("ws://localhost:8000/ws/dashboard", on_message=on_message)
    ws.run_forever()

if 'thread_started' not in st.session_state:
    thread = threading.Thread(target=run_ws, daemon=True)
    # هذا السطر هو الذي يربط الـ Thread بـ Streamlit ويحل مشكلة الـ ScriptRunContext
    add_script_run_ctx(thread) 
    thread.start()
    st.session_state.thread_started = True

# 5. الواجهة (تم تصحيح مكان زر اللغة)
st.sidebar.button(texts[st.session_state.lang]['lang_btn'], on_click=toggle_lang)
t = texts[st.session_state.lang]

st.title(f"🚀 {t['title']}")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(t['chart'])
    st.info("Market data sync active..." if st.session_state.lang == 'en' else "بيانات السوق متصلة...")

with col2:
    st.subheader(t['signals'])
    # هنا الجزء الأهم: عرض البيانات من الحالة مباشرة
    if st.session_state.last_signal:
        sig = st.session_state.last_signal
        st.markdown(f"""
        <div class="signal-box">
            <b>Action:</b> {sig.get('action', 'N/A')}<br>
            <b>Price:</b> {sig.get('entry', 'N/A')}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("No signals yet" if st.session_state.lang == 'en' else "لا توجد إشارات حالياً")

# تحديث تلقائي للصفحة كل ثانية لجلب البيانات من الـ state
import time
time.sleep(1)
st.rerun()