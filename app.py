import streamlit as st

st.set_page_config(page_title="Multi-Function WebApp", page_icon="🧰", layout="wide")

pages = [
    st.Page("pages/프롬프트생성기.py", title="프롬프트생성기", icon="✨", default=True),
    st.Page("pages/가상데이터생성기.py", title="가상데이터생성기", icon="🎭"),
    st.Page("pages/데이터클렌징.py", title="데이터클렌징", icon="🧹"),
    st.Page("pages/주가비교분석기.py", title="주가비교분석", icon="📈"),
    st.Page("pages/주가지수및환율.py", title="주가지수 및 환율", icon="💱"),
    st.Page("pages/대량양식생성기.py", title="대량양식생성기", icon="📄"),
    st.Page("pages/음원툴박스.py", title="음원툴박스", icon="🎧"),
    st.Page("pages/아파트실거래가조회.py", title="아파트실거래가조회", icon="🏢"),
]

with st.sidebar:
    st.markdown("## 🧰 Multi-Function WebApp")
    st.caption("위에서 사용할 기능을 선택하세요.")

nav = st.navigation(pages)
nav.run()
