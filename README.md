# 🧰 Multi-Function WebApp

여러 개의 독립적인 실무 도구를 하나의 Streamlit 앱에서 사이드바로 전환하며 사용할 수 있게 모은 멀티페이지 웹앱입니다.

최초 접속 시 각 기능을 카드 형태로 소개하는 🏠 홈 화면이 먼저 보이며, 사이드바는 "업무 도구 1 / 업무 도구 2 / 개인 관심사" 3개 그룹으로 구분되어 있습니다.

## 기능 목록

| 기능 | 설명 |
|---|---|
| ✨ 프롬프트생성기 | Gemini API를 이용해 요구사항을 최적화된 AI 프롬프트로 변환 (사이드바에서 "내 API 키 사용" 또는 "비밀번호로 접속"(사전 등록된 공용 키 사용) 중 선택) |
| 🎭 가상데이터생성기 | Faker 기반으로 보험/개인정보 등 가상 데이터를 생성해 Excel로 다운로드 |
| 🧹 데이터클렌징 | 업로드한 Excel의 행/열 정리·필터링·병합을 단계별로 적용 후 다운로드 |
| 📋 공시정보검색 | 금융감독원 DART API로 회사명을 검색해 최근 공시정보(공시일/보고서명/제출인/공시URL)를 표로 확인, 공시URL은 클릭하면 새 탭에서 열리는 하이퍼링크 |
| 📈 주가비교분석 | FinanceDataReader로 여러 종목의 주가를 조회하고 그래프로 비교 |
| 💱 주가지수 및 환율 | 한국은행 ECOS API로 코스피·코스닥 지수와 원/달러·원/엔 환율의 일별 추이를 2x2 그래프와 지표별 표로 확인, Excel 다운로드 |
| 📄 대량양식생성기 | PDF 양식에 Excel 데이터를 매핑해 대량으로 개별 PDF 생성 (ZIP 다운로드, 삽입 텍스트는 Pretendard Bold 폰트 내장) |
| 🎧 음원툴박스 | 유튜브 URL → MP3 추출, 텍스트 → 음성(TTS) 변환 |
| 🏢 아파트실거래가조회 | 공공데이터포털 API로 기간·지역(서울 25개 구)별 아파트 매매 실거래가를 조회해 표로 확인, Excel 다운로드 (API 키는 `secrets.toml`/Streamlit Cloud Secrets로 관리, 화면 입력 없음) |

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 배포 시 참고 사항 (Streamlit Community Cloud)

- **(2026-09-09) `packages.txt`를 사용하지 않습니다.** 이전에는 유튜브 MP3 추출(`ffmpeg`)과 주가비교분석 그래프 PNG 다운로드(`chromium`+`fonts-nanum`)를 위해 apt 패키지를 설치했으나, Streamlit Community Cloud 플랫폼 자체의 apt 저장소 문제(`bullseye-security` 인증서 만료 + `trixie` 소스 혼재)로 apt-get 단계가 통째로 실패해 앱이 아예 기동되지 않는 사태가 발생했습니다. 이를 계기로 두 기능 모두 **apt(시스템 패키지) 없이 순수 pip 라이브러리만으로 동작하도록 교체**했습니다:
  - 🎧 유튜브 MP3 추출: `yt_dlp`의 `ffmpeg_location`에 `imageio-ffmpeg` 패키지가 pip install 시 함께 내려받는 정적 ffmpeg 바이너리 경로를 지정 (`imageio_ffmpeg.get_ffmpeg_exe()`).
  - 📈 주가비교분석 PNG 다운로드: 기존 `kaleido`(헤드리스 브라우저 필요) 대신 `matplotlib`으로 동일한 그래프를 직접 렌더링. 한글 폰트도 시스템 설치 폰트가 아니라 리포에 이미 내장된 `assets/fonts/Pretendard-Bold.ttf`를 코드에서 직접 등록해서 사용하므로, 클라우드 컨테이너에 한글 폰트가 없어도 깨지지 않습니다.
  - 이 방식은 apt 저장소 문제와 완전히 무관해서, Streamlit Cloud의 base 이미지 상태와 상관없이 항상 안정적으로 동작합니다. `packages.txt` 파일 자체가 저장소에 없으므로 앱 시작 시 apt-get 단계가 아예 실행되지 않습니다.
- Gemini API 키는 코드에 저장되어 있지 않으며, 기본적으로 각 세션에서 사용자가 직접 입력합니다. 비밀번호로 공용 키를 사용하게 하려면 `.streamlit/secrets.toml`(로컬) 또는 Streamlit Cloud의 **Settings → Secrets**에 아래 두 값을 등록하세요.
  ```toml
  GEMINI_API_KEY = "공용으로_쓸_제미나이_키"
  APP_PASSWORD = "10자리_비밀번호(숫자+영문 대소문자+특수문자)"
  ```
  두 값 중 하나라도 비어 있으면 "비밀번호로 접속" 탭에서 안내 메시지만 표시되고, 본인 API 키 입력 방식은 그대로 동작합니다.
- 아파트실거래가조회 페이지는 공공데이터포털(data.go.kr) API 키가 필요합니다. 코드에 하드코딩하지 않고 `.streamlit/secrets.toml`(로컬, git 미포함)에서 읽어오며, Streamlit Cloud 배포 시에는 앱의 **Settings → Secrets**에 아래 값을 등록해야 합니다.
  ```toml
  DATA_GO_KR_API_KEY = "발급받은_키"
  ```
- 주가지수 및 환율 페이지는 한국은행 ECOS API 키가 필요합니다. 마찬가지로 `.streamlit/secrets.toml`(로컬, git 미포함)에서 읽어오며, Streamlit Cloud 배포 시에는 앱의 **Settings → Secrets**에 아래 값을 등록해야 합니다.
  ```toml
  ECOS_API_KEY = "발급받은_키"
  ```
- 공시정보검색 페이지는 금융감독원 DART Open API 키가 필요합니다. `.streamlit/secrets.toml`(로컬, git 미포함)에서 읽어오며, Streamlit Cloud 배포 시에는 앱의 **Settings → Secrets**에 아래 값을 등록해야 합니다.
  ```toml
  DART_API_KEY = "발급받은_키"
  ```
- 유튜브 MP3 추출 기능은 클라우드 서버의 IP 대역에 따라 유튜브 측에서 접근을 제한할 수 있습니다(로컬 환경보다 실패 가능성이 있음). 이를 완화하기 위해 `yt_dlp`가 웹 브라우저 대신 안드로이드/iOS 앱 클라이언트로 위장해 요청하도록 설정했지만(`extractor_args`의 `player_client`), 유튜브가 IP 자체를 차단한 경우에는 이 설정으로도 우회되지 않을 수 있습니다.
- 대량양식생성기가 삽입하는 텍스트는 `assets/fonts/Pretendard-Bold.ttf`를 사용합니다. 맑은고딕은 마이크로소프트 소유 폰트라 재배포할 수 없어, 느낌이 유사하고 SIL Open Font License로 자유롭게 배포 가능한 Pretendard Bold를 대신 내장했습니다(라이선스 전문: `assets/fonts/LICENSE-Pretendard.txt`).
