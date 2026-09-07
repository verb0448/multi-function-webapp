import io
import os
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datakart import Ecos
from plotly.subplots import make_subplots

st.title("💱 주가지수 및 환율")
st.caption("한국은행 ECOS(경제통계시스템) API로 코스피·코스닥 지수와 원/달러·원/엔 환율의 일별 추이를 조회합니다.")

INDICATORS = [
    ("코스피지수", "802Y001", "0001000"),
    ("코스닥지수", "802Y001", "0089000"),
    ("원달러환율", "731Y001", "0000001"),
    ("원엔환율", "731Y001", "0000002"),
]
CHART_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]


def get_api_key() -> str | None:
    try:
        key = st.secrets.get("ECOS_API_KEY")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("ECOS_API_KEY")


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def fetch_ecos_series(api_key: str, stat_code: str, item_code1: str, start: str, end: str) -> pd.DataFrame:
    ecos = Ecos(api_key)
    rows = ecos.stat_search(stat_code=stat_code, freq="D", item_code1=item_code1, start=start, end=end)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df[["TIME", "DATA_VALUE"]].copy()
    df["TIME"] = pd.to_datetime(df["TIME"], format="%Y%m%d")
    df["DATA_VALUE"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
    return df.sort_values("TIME").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="일별데이터")
    return buffer.getvalue()


# ============================================================
# API 키 - secrets.toml(로컬) 또는 Streamlit Cloud Secrets / 환경변수에서 읽어온다
# ============================================================
api_key = get_api_key()
if not api_key:
    st.error(
        "⚠️ ECOS_API_KEY가 설정되지 않았습니다. "
        "`.streamlit/secrets.toml`(로컬) 또는 Streamlit Cloud의 Secrets에 등록해주세요."
    )

# ============================================================
# 세션 상태
# ============================================================
if "ecos_data" not in st.session_state:
    st.session_state.ecos_data = None  # {name: df}

# ============================================================
# 입력 영역
# ============================================================
st.subheader("🔍 조회 조건")

start_date = st.date_input(
    "조회 시작일",
    value=date.today().replace(year=date.today().year - 1),
    max_value=date.today(),
    format="YYYY-MM-DD",
)

search_clicked = st.button("📊 지표 조회", type="primary")

if search_clicked:
    if not api_key:
        st.error("⚠️ API 키가 설정되지 않아 조회할 수 없습니다.")
    else:
        start_str = start_date.strftime("%Y%m%d")
        end_str = date.today().strftime("%Y%m%d")

        data = {}
        errors = []
        with st.spinner("ECOS에서 지표를 조회하는 중입니다..."):
            for name, stat_code, item_code1 in INDICATORS:
                try:
                    df = fetch_ecos_series(api_key, stat_code, item_code1, start_str, end_str)
                    if df.empty:
                        errors.append(f"'{name}'의 조회 결과가 없습니다.")
                    else:
                        data[name] = df
                except Exception as e:
                    errors.append(f"'{name}' 조회 중 오류: {e}")

        for err in errors:
            st.error(f"❌ {err}")

        if data:
            st.session_state.ecos_data = data
            st.success(f"✅ {len(data)}개 지표 조회 완료 ({start_date} ~ {date.today()})")
        else:
            st.session_state.ecos_data = None

# ============================================================
# 결과 영역
# ============================================================
st.divider()

if st.session_state.ecos_data:
    data = st.session_state.ecos_data
    names = list(data.keys())

    # 2행 2열 그래프
    st.subheader("📊 지표 추이 (2x2)")
    fig = make_subplots(rows=2, cols=2, subplot_titles=names)
    for i, name in enumerate(names):
        df = data[name]
        row, col = i // 2 + 1, i % 2 + 1
        fig.add_trace(
            go.Scatter(
                x=df["TIME"],
                y=df["DATA_VALUE"],
                mode="lines",
                name=name,
                line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=1.5),
            ),
            row=row,
            col=col,
        )
    fig.update_layout(height=700, showlegend=False, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # 지표별 상세 데이터
    st.subheader("📋 지표별 일별 데이터")
    tabs = st.tabs(names)
    for tab, name in zip(tabs, names):
        with tab:
            df = data[name].rename(columns={"TIME": "날짜", "DATA_VALUE": name})
            df["날짜"] = df["날짜"].dt.strftime("%Y-%m-%d")
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.download_button(
                label=f"📥 {name} 데이터 Excel 다운로드",
                data=to_excel_bytes(df),
                file_name=f"{name}_{start_date}~{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_excel_{name}",
            )
else:
    st.info("조회 시작일을 입력한 뒤 '지표 조회' 버튼을 클릭하세요.")
