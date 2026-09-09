import streamlit as st

st.title("🧰 Multi-Function WebApp")
st.caption("여러 업무·개인 도구를 한곳에 모은 웹앱입니다. 왼쪽 메뉴 또는 아래 카드에서 원하는 기능을 선택하세요.")

FEATURE_GROUPS = [
    (
        "📁 업무 도구 1",
        [
            ("pages/프롬프트생성기.py", "✨", "프롬프트생성기", "Gemini API로 요구사항을 최적화된 AI 프롬프트로 변환"),
            ("pages/가상데이터생성기.py", "🎭", "가상데이터생성기", "Faker 기반 가상 데이터 생성, Excel 다운로드"),
            ("pages/데이터클렌징.py", "🧹", "데이터클렌징", "Excel 행/열 정리·필터링·병합 후 다운로드"),
            ("pages/대량양식생성기.py", "📄", "대량양식생성기", "PDF 양식에 Excel 데이터를 매핑해 대량 생성"),
        ],
    ),
    (
        "📁 업무 도구 2",
        [
            ("pages/공시정보검색.py", "📋", "공시정보검색", "DART API로 회사 공시정보 검색"),
            ("pages/주가비교분석기.py", "📈", "주가비교분석", "여러 종목의 주가를 조회하고 비교"),
            ("pages/주가지수및환율.py", "💱", "주가지수 및 환율", "코스피·코스닥·환율의 일별 추이 확인"),
        ],
    ),
    (
        "🎧 개인 관심사",
        [
            ("pages/음원툴박스.py", "🎧", "음원툴박스", "유튜브 MP3 추출, 텍스트 음성 변환"),
            ("pages/아파트실거래가조회.py", "🏢", "아파트실거래가조회", "지역·기간별 아파트 매매 실거래가 조회"),
        ],
    ),
]

for group_title, features in FEATURE_GROUPS:
    st.subheader(group_title)
    cols = st.columns(len(features))
    for col, (path, icon, name, desc) in zip(cols, features):
        with col:
            with st.container(border=True):
                st.markdown(f"##### {icon} {name}")
                st.caption(desc)
                st.page_link(path, label="바로가기", icon="➡️")
    st.write("")
