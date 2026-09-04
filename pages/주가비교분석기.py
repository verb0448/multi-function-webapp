import datetime
import difflib

import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

MAX_COMPANIES = 5


@st.cache_data(ttl=6 * 60 * 60, show_spinner="KRX 상장사 목록을 불러오는 중입니다...")
def load_krx_listing() -> pd.DataFrame:
    df = fdr.StockListing("KRX")
    return df[["Code", "Name", "Market"]].dropna(subset=["Name"])


@st.cache_data(show_spinner=False)
def fetch_price_data(code: str, start_date: str) -> pd.DataFrame:
    return fdr.DataReader(code, start_date)


CHART_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]


def build_comparison_chart(price_data: dict, start_date, end_date) -> go.Figure:
    fig = go.Figure()

    for i, (name, df) in enumerate(price_data.items()):
        color = CHART_COLORS[i % len(CHART_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Close"],
                mode="lines",
                name=name,
                line=dict(color=color),
            )
        )

        # 기간 내 최고가 / 최저가 지점을 마커 + 주석으로 표시
        max_idx = df["Close"].idxmax()
        min_idx = df["Close"].idxmin()
        max_price = df.loc[max_idx, "Close"]
        min_price = df.loc[min_idx, "Close"]

        fig.add_trace(
            go.Scatter(
                x=[max_idx, min_idx],
                y=[max_price, min_price],
                mode="markers",
                marker=dict(color=color, size=10, symbol=["triangle-up", "triangle-down"], line=dict(width=1, color="white")),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        # 여러 회사의 극값이 비슷한 위치에 몰릴 경우를 대비해 회사마다 세로 오프셋을 다르게 준다
        offset = i * 22
        fig.add_annotation(
            x=max_idx,
            y=max_price,
            text=f"{name} 최고<br>{max_price:,.0f} ({max_idx.strftime('%Y-%m-%d')})",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-35 - offset,
            font=dict(size=10, color=color),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor=color,
        )
        fig.add_annotation(
            x=min_idx,
            y=min_price,
            text=f"{name} 최저<br>{min_price:,.0f} ({min_idx.strftime('%Y-%m-%d')})",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=35 + offset,
            font=dict(size=10, color=color),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor=color,
        )

    fig.update_layout(
        title=f"주가 비교 ({start_date} ~ {end_date})",
        xaxis_title="날짜",
        yaxis_title="종가 (원)",
        legend_title="회사",
        hovermode="x unified",
        template="plotly_white",
    )
    return fig


# ============================================================
# 세션 상태 초기화
# ============================================================
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []  # [{"name": str, "code": str}, ...]
if "stock_price_data" not in st.session_state:
    st.session_state.stock_price_data = None  # {name: df}
if "stock_query_meta" not in st.session_state:
    st.session_state.stock_query_meta = None  # {start_date, end_date}
if "stock_chart_png" not in st.session_state:
    st.session_state.stock_chart_png = None


def remove_from_watchlist(idx: int):
    st.session_state.watchlist.pop(idx)


st.title("📈 주가 비교 분석기")
st.caption("FinanceDataReader로 한국거래소(KRX) 상장사의 주가를 조회하고, 여러 종목을 한 그래프에서 비교합니다.")

krx_df = load_krx_listing()
name_to_code = dict(zip(krx_df["Name"], krx_df["Code"]))
all_names = krx_df["Name"].tolist()

# ============================================================
# 입력 영역 - 종목을 하나씩 추가해 최대 5개까지 목록을 구성
# ============================================================
st.subheader("🔍 조회할 종목 추가")

with st.form("add_company_form", clear_on_submit=True):
    add_col1, add_col2 = st.columns([4, 1])
    with add_col1:
        new_company_name = st.text_input(
            "회사 이름",
            placeholder="예: 삼성전자",
            label_visibility="collapsed",
        )
    with add_col2:
        add_submitted = st.form_submit_button("➕ 종목 추가", use_container_width=True)

if add_submitted:
    name = new_company_name.strip()
    existing_names = [c["name"] for c in st.session_state.watchlist]
    if not name:
        st.warning("⚠️ 회사 이름을 입력해주세요.")
    elif len(st.session_state.watchlist) >= MAX_COMPANIES:
        st.warning(f"⚠️ 최대 {MAX_COMPANIES}개까지만 추가할 수 있습니다. 조회하려면 기존 종목을 먼저 제거해주세요.")
    elif name in existing_names:
        st.warning(f"⚠️ '{name}'은(는) 이미 추가되어 있습니다.")
    else:
        code = name_to_code.get(name)
        if code is None:
            suggestions = difflib.get_close_matches(name, all_names, n=3, cutoff=0.6)
            if suggestions:
                st.warning(f"⚠️ '{name}' 종목을 찾을 수 없습니다. 혹시 이 중 하나인가요? {', '.join(suggestions)}")
            else:
                st.warning(f"⚠️ '{name}' 종목을 찾을 수 없습니다. 정확한 회사명을 입력해주세요.")
        else:
            st.session_state.watchlist.append({"name": name, "code": code})

# 추가된 종목 목록 (제거 가능한 칩 형태)
if st.session_state.watchlist:
    st.caption(f"추가된 종목 ({len(st.session_state.watchlist)}/{MAX_COMPANIES})")
    chip_cols = st.columns(MAX_COMPANIES)
    for i, comp in enumerate(st.session_state.watchlist):
        with chip_cols[i]:
            st.button(
                f"❌ {comp['name']}",
                key=f"remove_watchlist_{i}",
                on_click=remove_from_watchlist,
                args=(i,),
                use_container_width=True,
            )
else:
    st.caption("아직 추가된 종목이 없습니다.")

default_start = datetime.date.today() - datetime.timedelta(days=365)
start_date = st.date_input("조회 시작일자", value=default_start, max_value=datetime.date.today())

search_clicked = st.button("📊 주식 정보 조회", type="primary")

if search_clicked:
    if not st.session_state.watchlist:
        st.error("⚠️ 조회할 종목을 최소 1개 이상 추가해주세요.")
    else:
        price_data = {}
        fetch_errors = []
        with st.spinner("주가 데이터를 조회하는 중입니다..."):
            for comp in st.session_state.watchlist:
                name, code = comp["name"], comp["code"]
                try:
                    df = fetch_price_data(code, start_date.isoformat())
                    if df.empty:
                        fetch_errors.append(f"'{name}'({code})의 조회 결과가 없습니다.")
                    else:
                        price_data[name] = df
                except Exception as e:
                    fetch_errors.append(f"'{name}'({code}) 조회 중 오류: {e}")

        for err in fetch_errors:
            st.error(f"❌ {err}")

        if price_data:
            end_date = max(df.index.max() for df in price_data.values()).date()
            st.session_state.stock_price_data = price_data
            st.session_state.stock_query_meta = {
                "start_date": start_date,
                "end_date": end_date,
            }
            fig = build_comparison_chart(price_data, start_date, end_date)
            try:
                st.session_state.stock_chart_png = fig.to_image(format="png", width=1600, height=800, scale=2)
            except Exception:
                st.session_state.stock_chart_png = None
            st.success(f"✅ {len(price_data)}개 종목 조회 완료 (기준일: {end_date})")

# ============================================================
# 결과 영역
# ============================================================
st.divider()

if st.session_state.stock_price_data:
    price_data = st.session_state.stock_price_data
    meta = st.session_state.stock_query_meta
    names = list(price_data.keys())

    # 오늘(최신 거래일) 현황 스냅샷
    st.subheader(f"📌 최신 현황 (기준일: {meta['end_date']})")
    cols = st.columns(len(names))
    for col, name in zip(cols, names):
        df = price_data[name]
        latest = df.iloc[-1]
        change_pct = latest.get("Change", 0) * 100
        col.metric(label=name, value=f"{latest['Close']:,.0f}원", delta=f"{change_pct:+.2f}%")

    # 비교 그래프
    st.subheader("📊 주가 비교 그래프")
    fig = build_comparison_chart(price_data, meta["start_date"], meta["end_date"])
    st.plotly_chart(fig, use_container_width=True)

    if st.session_state.stock_chart_png:
        st.download_button(
            label="🖼️ 그래프 이미지 다운로드 (PNG)",
            data=st.session_state.stock_chart_png,
            file_name=f"주가비교_{'_'.join(names)}_{meta['start_date']}~{meta['end_date']}.png",
            mime="image/png",
        )
    else:
        st.caption("⚠️ 이미지 생성에 실패하여 PNG 다운로드를 사용할 수 없습니다.")

    # 조회된 모든 회사의 상세 데이터 (탭으로 구분, 각각 다운로드 가능)
    st.subheader("📋 종목별 상세 데이터")
    tabs = st.tabs(names)
    for tab, name in zip(tabs, names):
        with tab:
            company_df = price_data[name].reset_index()
            company_df["Date"] = company_df["Date"].dt.strftime("%Y-%m-%d")
            company_df["Change"] = (company_df["Change"] * 100).round(1).map(lambda v: f"{v:.1f}%")
            company_df = company_df.rename(
                columns={
                    "Date": "날짜",
                    "Open": "시가",
                    "High": "고가",
                    "Low": "저가",
                    "Close": "종가",
                    "Volume": "거래량",
                    "Change": "등락률",
                }
            )
            st.dataframe(company_df, use_container_width=True)

            csv_bytes = company_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label=f"📥 {name} 데이터 CSV 다운로드",
                data=csv_bytes,
                file_name=f"{name}_{meta['start_date']}~{meta['end_date']}_주가데이터.csv",
                mime="text/csv",
                key=f"download_csv_{name}",
            )
else:
    st.info("회사 이름과 조회 시작일을 입력한 뒤 '주식 정보 조회' 버튼을 클릭하세요.")
