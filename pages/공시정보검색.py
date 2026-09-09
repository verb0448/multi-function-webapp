import os
import zipfile
from datetime import date
from io import BytesIO

import pandas as pd
import requests
import streamlit as st
import xmltodict

st.title("📋 공시정보검색")
st.caption("금융감독원 DART(전자공시시스템) API로 회사명을 검색해 최근 공시정보를 조회합니다.")


def get_api_key() -> str | None:
    try:
        key = st.secrets.get("DART_API_KEY")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("DART_API_KEY")


@st.cache_data(ttl=24 * 60 * 60, show_spinner="회사 목록을 불러오는 중입니다...")
def load_corp_list(api_key: str) -> pd.DataFrame:
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    zip_file = zipfile.ZipFile(BytesIO(resp.content))
    xml_data = zip_file.read("CORPCODE.xml").decode("utf-8")
    records = xmltodict.parse(xml_data)["result"]["list"]
    df = pd.DataFrame(records)
    return df.dropna(subset=["corp_name"])


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def fetch_notices(api_key: str, corp_code: str, count: int) -> pd.DataFrame:
    url = (
        "https://opendart.fss.or.kr/api/list.json"
        f"?crtfc_key={api_key}&corp_code={corp_code}"
        "&bgn_de=19990101"
        f"&end_de={date.today().strftime('%Y%m%d')}"
        "&sort=date&sort_mth=desc"
        f"&page_no=1&page_count={count}"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    status = payload.get("status")
    if status == "013":  # 조회된 공시가 없는 경우 (DART API 정상 응답)
        return pd.DataFrame()
    if status != "000":
        raise RuntimeError(payload.get("message", "알 수 없는 오류가 발생했습니다."))

    df = pd.DataFrame(payload.get("list", []))
    if df.empty:
        return df

    df = df[["rcept_dt", "report_nm", "flr_nm", "rcept_no"]].rename(
        columns={"rcept_dt": "공시일", "report_nm": "보고서명", "flr_nm": "제출인", "rcept_no": "공시번호"}
    )
    df["공시URL"] = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + df["공시번호"]
    return df[["공시일", "보고서명", "제출인", "공시URL"]]


# ============================================================
# API 키
# ============================================================
api_key = get_api_key()
if not api_key:
    st.error(
        "⚠️ DART_API_KEY가 설정되지 않았습니다. "
        "`.streamlit/secrets.toml`(로컬) 또는 Streamlit Cloud의 Secrets에 등록해주세요."
    )
    st.stop()

try:
    corp_list = load_corp_list(api_key)
except Exception:
    st.error("⚠️ 회사 목록을 불러오지 못했습니다. 잠시 후 새로고침해 다시 시도해주세요.")
    st.stop()

# ============================================================
# 세션 상태
# ============================================================
if "dart_notice_result" not in st.session_state:
    st.session_state.dart_notice_result = None
if "dart_notice_meta" not in st.session_state:
    st.session_state.dart_notice_meta = None

# ============================================================
# 입력 영역
# ============================================================
st.subheader("🔍 조회할 회사 검색")

search_term = st.text_input("회사 이름", placeholder="예: 삼성전자")

selected_corp_code = None
selected_corp_name = None
if search_term.strip():
    term = search_term.strip()
    matches = corp_list[corp_list["corp_name"].str.contains(term, case=False, na=False)].drop_duplicates(
        subset="corp_name"
    )
    # 정확히 일치하거나 검색어로 시작하는 회사명이 먼저 보이도록 정렬 (예: "삼성전자" 검색 시
    # "삼성전자서비스" 같은 계열사보다 "삼성전자" 자체가 상단에 오도록)
    matches = matches.assign(
        _rank=matches["corp_name"].map(
            lambda name: 0 if name == term else (1 if name.startswith(term) else 2)
        )
    ).sort_values(["_rank", "corp_name"]).head(20)
    if matches.empty:
        st.warning(f"⚠️ '{search_term}'이(가) 포함된 회사를 찾을 수 없습니다.")
    else:
        selected_corp_name = st.selectbox("검색된 회사 중 선택", matches["corp_name"].tolist())
        selected_corp_code = matches.loc[matches["corp_name"] == selected_corp_name, "corp_code"].iloc[0]

count = st.slider("조회할 공시 건수", min_value=10, max_value=100, step=10, value=20)

search_clicked = st.button("📋 공시정보 조회", type="primary")

if search_clicked:
    if not selected_corp_code:
        st.error("⚠️ 회사를 먼저 검색하고 선택해주세요.")
    else:
        try:
            with st.spinner(f"'{selected_corp_name}'의 공시정보를 조회하는 중입니다..."):
                notice_df = fetch_notices(api_key, selected_corp_code, count)
        except Exception as e:
            st.error(f"❌ 조회 중 오류가 발생했습니다: {e}")
            notice_df = None

        if notice_df is not None:
            if notice_df.empty:
                st.warning(f"⚠️ '{selected_corp_name}'의 공시정보가 없습니다.")
                st.session_state.dart_notice_result = None
            else:
                st.session_state.dart_notice_result = notice_df
                st.session_state.dart_notice_meta = {"corp_name": selected_corp_name, "count": len(notice_df)}
                st.success(f"✅ '{selected_corp_name}' 공시정보 {len(notice_df)}건 조회 완료")

# ============================================================
# 결과 영역
# ============================================================
st.divider()

if st.session_state.dart_notice_result is not None:
    notice_df = st.session_state.dart_notice_result
    meta = st.session_state.dart_notice_meta

    st.subheader(f"📄 '{meta['corp_name']}' 공시정보 ({meta['count']}건)")
    st.dataframe(
        notice_df,
        column_config={
            "공시URL": st.column_config.LinkColumn("공시URL", display_text="🔗 공시 보기"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("회사 이름을 검색하고 목록에서 선택한 뒤 '공시정보 조회' 버튼을 클릭하세요.")
