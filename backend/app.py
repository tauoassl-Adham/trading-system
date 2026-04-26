import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide") # هذا يفتح الواجهة على كامل الشاشة

st.title("المنصة المؤسسية للتداول")

# توزيع الواجهة (Sidebar للمحفظة، وColumns للمعلومات)
with st.sidebar:
    st.header("المحفظة")
    st.metric("الرصيد الحالي", "$10,000", "+5%")
    st.subheader("الأخبار")
    st.write("• صعود البيتكوين بنسبة 2%...")

# منطقة الشارتات
col1, col2 = st.columns([3, 1]) # تقسيم: 75% للشارت، 25% للبيانات
with col1:
    st.subheader("شارت السعر اللحظي")
    # هنا سنربط Plotly لاحقاً
    st.line_chart(pd.DataFrame({'السعر': [100, 102, 101, 105]}))

with col2:
    st.subheader("سجل الطلبات")
    st.write("سعر الشراء: 104.5")
    st.write("سعر البيع: 104.6")