import streamlit as st

# 그룹별 포인트 컬러 - 업무 도구는 차분한 파랑·보라 계열, 개인 관심사는 따뜻한 톤으로 구분한다.
FEATURE_GROUPS = [
    (
        "업무 도구 1",
        "#3b82f6",
        [
            ("pages/프롬프트생성기.py", "✨", "프롬프트생성기", "Gemini API로 요구사항을 최적화된 AI 프롬프트로 변환"),
            ("pages/가상데이터생성기.py", "🎭", "가상데이터생성기", "Faker 기반 가상 데이터 생성, Excel 다운로드"),
            ("pages/데이터클렌징.py", "🧹", "데이터클렌징", "Excel 행/열 정리·필터링·병합 후 다운로드"),
            ("pages/대량양식생성기.py", "📄", "대량양식생성기", "PDF 양식에 Excel 데이터를 매핑해 대량 생성"),
            ("pages/문서스캔변환기.py", "📐", "문서스캔변환기", "비스듬한 서류 사진의 4꼭짓점을 클릭해 반듯한 이미지로 보정"),
        ],
    ),
    (
        "업무 도구 2",
        "#8b5cf6",
        [
            ("pages/공시정보검색.py", "📋", "공시정보검색", "DART API로 회사 공시정보 검색"),
            ("pages/주가비교분석기.py", "📈", "주가비교분석", "여러 종목의 주가를 조회하고 비교"),
            ("pages/주가지수및환율.py", "💱", "주가지수 및 환율", "코스피·코스닥·환율의 일별 추이 확인"),
        ],
    ),
    (
        "개인 관심사",
        "#f59e0b",
        [
            (
                "pages/음원툴박스.py",
                "🎧",
                "음원툴박스",
                "유튜브 MP3 추출, 텍스트 음성 변환<br><br>※ 유튜브 정책에 따라 유튜브 음원 추출 불가할 수 있음",
            ),
            ("pages/아파트실거래가조회.py", "🏢", "아파트실거래가조회", "지역·기간별 아파트 매매 실거래가 조회"),
        ],
    ),
]

CARD_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

.home-hero-title {
    font-family: 'Pretendard', sans-serif;
    font-weight: 800;
    font-size: 2.4rem;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #6366f1, #ec4899);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    margin-bottom: 0.3rem;
}
.home-hero-underline {
    width: 64px;
    height: 5px;
    border-radius: 3px;
    background: linear-gradient(90deg, #6366f1, #ec4899);
    margin-bottom: 1.1rem;
}
.home-hero-caption {
    color: #6b7280;
    font-size: 0.95rem;
    margin-bottom: 0.5rem;
}
.home-group-header {
    display: flex;
    align-items: center;
    border-left: 5px solid var(--accent);
    padding-left: 12px;
    font-size: 1.15rem;
    font-weight: 700;
    color: #1f2333;
    margin: 2rem 0 0.9rem;
}
.home-card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
}
.home-feature-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 168px;
    padding: 20px;
    border-radius: 16px;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    text-decoration: none !important;
    color: inherit;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}
.home-feature-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 14px 26px rgba(0, 0, 0, 0.12);
    border-color: var(--accent);
    background: color-mix(in srgb, var(--accent) 6%, white);
}
.home-feature-card .card-icon {
    font-size: 1.7rem;
}
.home-feature-card .card-title {
    font-weight: 700;
    font-size: 1.05rem;
    color: #111827;
}
.home-feature-card .card-desc {
    font-size: 0.85rem;
    color: #6b7280;
    line-height: 1.45;
    flex-grow: 1;
}
.home-logo-bar {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 1.2rem;
}
.brand-logo {
    background: #0D1E6C;
    border-radius: 8px;
    padding: 6px 12px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 0;
    flex-shrink: 0;
}
.brand-logo img {
    display: block;
    height: 40px;
    width: auto;
    max-width: 260px;
    object-fit: contain;
}
</style>
"""

st.markdown(CARD_CSS, unsafe_allow_html=True)

logo_html = """
<div class="home-logo-bar">
    <div class="brand-logo"><img src="https://i.postimg.cc/vBjqSL4T/logo.png" alt="로고"></div>
</div>
"""
st.markdown(logo_html, unsafe_allow_html=True)

hero_html = """
<div class="home-hero-title">모듈형 Multi-Function 웹앱</div>
<div class="home-hero-underline"></div>
<div class="home-hero-caption">여러 업무·개인 도구를 한곳에 모은 웹앱입니다. 아래 카드를 클릭해 원하는 기능으로 이동하세요.</div>
"""
st.markdown(hero_html, unsafe_allow_html=True)

# 카드는 <a target="_self">로 만든다. target을 명시하지 않으면 Streamlit이
# 보안을 위해 자동으로 target="_blank"를 붙여 새 탭으로 열리므로, 지금 화면에서
# 그대로 전환되도록 target을 직접 지정해 그 기본 동작을 덮어썼다.
for group_title, accent, features in FEATURE_GROUPS:
    cards_html = "".join(
        '<a class="home-feature-card" href="{href}" target="_self" style="--accent:{accent}">'
        '<div class="card-icon">{icon}</div>'
        '<div class="card-title">{name}</div>'
        '<div class="card-desc">{desc}</div>'
        "</a>".format(
            href=path.replace("pages/", "/").replace(".py", ""),
            accent=accent,
            icon=icon,
            name=name,
            desc=desc,
        )
        for path, icon, name, desc in features
    )
    group_html = (
        f'<div class="home-group-header" style="--accent:{accent}">{group_title}</div>'
        f'<div class="home-card-grid">{cards_html}</div>'
    )
    st.markdown(group_html, unsafe_allow_html=True)
