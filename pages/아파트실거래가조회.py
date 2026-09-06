import io
import os
import re

import pandas as pd
import streamlit as st
from datakart import Datagokr

st.title("🏢 아파트 실거래가 조회")
st.caption("공공데이터포털(국토교통부) 아파트 매매 실거래가 API로 기간·지역별 거래 내역을 조회합니다.")

# 서울 25개 자치구 법정동코드(5자리, 통계청 고시 기준 - 값이 바뀌지 않는 고정 코드라 API 호출 없이 상수로 관리)
SEOUL_GU_CODES = {
    "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
    "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
    "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
    "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
    "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
    "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710",
    "강동구": "11740",
}

VIEW_OPTIONS = ["전체", "상위 100", "상위 300", "하위 100", "하위 300"]
YYYYMM_PATTERN = re.compile(r"^\d{6}$")


def get_api_key() -> str | None:
    try:
        key = st.secrets.get("DATA_GO_KR_API_KEY")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("DATA_GO_KR_API_KEY")


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def fetch_trade(api_key: str, lawd_code: str, deal_ym: str) -> pd.DataFrame:
    datago = Datagokr(api_key)
    items = datago.apt_trade(lawd_code, deal_ym)
    return pd.DataFrame(items)


def month_range(start_ym: str, end_ym: str) -> list[str]:
    start = int(start_ym[:4]) * 12 + int(start_ym[4:]) - 1
    end = int(end_ym[:4]) * 12 + int(end_ym[4:]) - 1
    months = []
    for m in range(start, end + 1):
        y, mo = divmod(m, 12)
        months.append(f"{y:04d}{mo + 1:02d}")
    return months


# ============================================================
# API 키 - secrets.toml(로컬) 또는 Streamlit Cloud Secrets / 환경변수에서 읽어온다 (화면 입력 없음)
# ============================================================
api_key = get_api_key()
if not api_key:
    st.error(
        "⚠️ DATA_GO_KR_API_KEY가 설정되지 않았습니다. "
        "`.streamlit/secrets.toml`(로컬) 또는 Streamlit Cloud의 Secrets에 등록해주세요."
    )

# ============================================================
# 세션 상태
# ============================================================
if "apt_trade_result" not in st.session_state:
    st.session_state.apt_trade_result = None
if "apt_trade_meta" not in st.session_state:
    st.session_state.apt_trade_meta = None

# ============================================================
# 입력 영역
# ============================================================
st.subheader("🔍 조회 조건")

col1, col2 = st.columns(2)
with col1:
    start_ym = st.text_input("시작 (YYYYMM)", value="202601", placeholder="예: 202601")
with col2:
    end_ym = st.text_input("종료 (YYYYMM)", value="202608", placeholder="예: 202608")

region = st.selectbox("지역", ["서울 전체"] + sorted(SEOUL_GU_CODES.keys()))

search_clicked = st.button("📊 실거래가 조회", type="primary")

if search_clicked:
    if not api_key:
        st.error("⚠️ API 키가 설정되지 않아 조회할 수 없습니다.")
    elif not (YYYYMM_PATTERN.match(start_ym) and YYYYMM_PATTERN.match(end_ym)):
        st.error("⚠️ 기간은 YYYYMM 형식의 6자리 숫자로 입력해주세요. (예: 202601)")
    elif start_ym > end_ym:
        st.error("⚠️ 시작 월이 종료 월보다 늦을 수 없습니다.")
    else:
        months = month_range(start_ym, end_ym)
        lawd_codes = list(SEOUL_GU_CODES.values()) if region == "서울 전체" else [SEOUL_GU_CODES[region]]
        code_to_name = {v: k for k, v in SEOUL_GU_CODES.items()}

        rows = []
        errors = []
        total = len(months) * len(lawd_codes)
        progress = st.progress(0.0)
        status = st.empty()
        done = 0

        for lawd_code in lawd_codes:
            gu_name = code_to_name[lawd_code]
            for deal_ym in months:
                status.text(f"조회 중... {gu_name} {deal_ym} ({done + 1}/{total})")
                try:
                    df_raw = fetch_trade(api_key, lawd_code, deal_ym)
                    if not df_raw.empty:
                        rows.append(df_raw)
                except Exception as e:
                    errors.append(f"{gu_name} {deal_ym} 조회 실패: {e}")
                done += 1
                progress.progress(done / total)

        progress.empty()
        status.empty()

        for err in errors:
            st.error(f"❌ {err}")

        if rows:
            df_all = pd.concat(rows, ignore_index=True)
            df_all["거래월"] = df_all["dealYear"].astype(str) + "-" + df_all["dealMonth"].astype(str).str.zfill(2)
            df_all["실거래가"] = df_all["dealAmount"].astype(str).str.replace(",", "").str.strip().astype(int)
            df_all["전용면적"] = df_all["excluUseAr"].astype(float)
            df_all = df_all.rename(columns={"aptNm": "아파트명", "umdNm": "행정동"})

            df_result = df_all[["아파트명", "거래월", "실거래가", "전용면적", "행정동"]]
            df_result = df_result.sort_values("실거래가", ascending=False).reset_index(drop=True)

            st.session_state.apt_trade_result = df_result
            st.session_state.apt_trade_meta = {"region": region, "start_ym": start_ym, "end_ym": end_ym}
            st.success(f"✅ {len(df_result)}건 조회 완료")
        elif not errors:
            st.session_state.apt_trade_result = None
            st.session_state.apt_trade_meta = None
            st.info("조회된 거래 내역이 없습니다.")

# ============================================================
# 결과 영역
# ============================================================
st.divider()

if st.session_state.apt_trade_result is not None:
    df_result = st.session_state.apt_trade_result

    view = st.radio("표시 범위", VIEW_OPTIONS, horizontal=True)
    if view == "전체":
        df_view = df_result
    elif view == "상위 100":
        df_view = df_result.head(100)
    elif view == "상위 300":
        df_view = df_result.head(300)
    elif view == "하위 100":
        df_view = df_result.tail(100)
    else:
        df_view = df_result.tail(300)

    st.caption(f"전체 {len(df_result)}건 중 {len(df_view)}건 표시 (실거래가 내림차순, 단위: 만원 / ㎡)")
    st.dataframe(
        df_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "실거래가": st.column_config.NumberColumn("실거래가", format="%,d"),
            "전용면적": st.column_config.NumberColumn("전용면적", format="%.2f"),
        },
    )

    meta = st.session_state.apt_trade_meta
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_view.to_excel(writer, index=False, sheet_name="실거래가")
    st.download_button(
        label="📥 엑셀 다운로드",
        data=excel_buffer.getvalue(),
        file_name=f"아파트실거래가_{meta['region']}_{meta['start_ym']}~{meta['end_ym']}_{view}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("조회 조건을 입력한 뒤 '실거래가 조회' 버튼을 클릭하세요.")
