# 🧰 Multi-Function WebApp

여러 개의 독립적인 실무 도구를 하나의 Streamlit 앱에서 사이드바로 전환하며 사용할 수 있게 모은 멀티페이지 웹앱입니다.

## 기능 목록

| 기능 | 설명 |
|---|---|
| ✨ 프롬프트생성기 | Gemini API를 이용해 요구사항을 최적화된 AI 프롬프트로 변환 (API 키는 사용자가 직접 입력, 서버에 저장하지 않음) |
| 🎭 가상데이터생성기 | Faker 기반으로 보험/개인정보 등 가상 데이터를 생성해 Excel로 다운로드 |
| 🧹 데이터클렌징 | 업로드한 Excel의 행/열 정리·필터링·병합을 단계별로 적용 후 다운로드 |
| 📈 주가비교분석 | FinanceDataReader로 여러 종목의 주가를 조회하고 그래프로 비교 |
| 📄 대량양식생성기 | PDF 양식에 Excel 데이터를 매핑해 대량으로 개별 PDF 생성 (ZIP 다운로드) |
| 🎧 음원툴박스 | 유튜브 URL → MP3 추출, 텍스트 → 음성(TTS) 변환 |
| 🏢 아파트실거래가조회 | 공공데이터포털 API로 기간·지역(서울 25개 구)별 아파트 매매 실거래가를 조회해 표로 확인, Excel 다운로드 (API 키는 `secrets.toml`/Streamlit Cloud Secrets로 관리, 화면 입력 없음) |

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 배포 시 참고 사항 (Streamlit Community Cloud)

- `packages.txt`에 `ffmpeg`(유튜브 MP3 추출), `chromium`(주가비교분석 그래프 PNG 다운로드용 kaleido 렌더링)이 등록되어 있어야 합니다. 둘 다 apt 패키지로 자동 설치됩니다.
- Gemini API 키는 코드에 저장되어 있지 않으며, 각 세션에서 사용자가 직접 입력합니다.
- 아파트실거래가조회 페이지는 공공데이터포털(data.go.kr) API 키가 필요합니다. 코드에 하드코딩하지 않고 `.streamlit/secrets.toml`(로컬, git 미포함)에서 읽어오며, Streamlit Cloud 배포 시에는 앱의 **Settings → Secrets**에 아래 값을 등록해야 합니다.
  ```toml
  DATA_GO_KR_API_KEY = "발급받은_키"
  ```
- 유튜브 MP3 추출 기능은 클라우드 서버의 IP 대역에 따라 유튜브 측에서 접근을 제한할 수 있습니다(로컬 환경보다 실패 가능성이 있음).
