import datetime
import io
import json
import os

import pandas as pd
import requests
import streamlit as st

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MODEL_OPTIONS = {
    "Gemini 2.5 Flash (빠르고 저렴)": "gemini-2.5-flash",
    "Gemini 2.5 Pro (고품질)": "gemini-2.5-pro",
}


def get_secret(name: str) -> str | None:
    try:
        val = st.secrets.get(name)
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(name)


@st.cache_data(show_spinner=False)
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="프롬프트 기록")
    return buffer.getvalue()


def build_meta_prompt(user_input: str, output_in_english: bool) -> str:
    lang_instruction = (
        "The generated prompt MUST be written entirely in English."
        if output_in_english
        else "생성된 프롬프트는 반드시 한국어로 작성해주세요."
    )
    return f"""당신은 세계 최고의 AI 프롬프트 엔지니어입니다.
사용자의 요구사항을 분석하여 AI(ChatGPT, Claude, Gemini 등)에서 최고의 결과를 얻을 수 있는 최적화된 프롬프트를 작성해주세요.

[프롬프트 작성 원칙]
1. 명확한 역할 부여 (페르소나 설정)
2. 구체적이고 명확한 지시사항
3. 출력 형식 및 품질 기준 명시
4. 필요시 예시 포함
5. 단계별 사고(Chain of Thought) 유도
6. 제약 조건 및 주의사항 명시

{lang_instruction}

[사용자 요구사항]
{user_input}

위 요구사항을 바탕으로 AI에서 최적의 결과를 얻을 수 있는 완성된 프롬프트만 작성해주세요.
설명이나 메타 코멘트 없이 바로 사용할 수 있는 프롬프트 본문만 출력하세요."""


def call_gemini(api_key: str, model: str, meta_prompt: str) -> dict:
    payload = {
        "contents": [{"parts": [{"text": meta_prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        },
    }
    url = GEMINI_API_URL.format(model=model)
    resp = requests.post(url, params={"key": api_key}, json=payload, timeout=60)

    if resp.status_code != 200:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except ValueError:
            detail = resp.text
        return {"success": False, "error": f"API 오류 ({resp.status_code}): {detail}"}

    data = resp.json()
    candidates = data.get("candidates")
    if not candidates:
        return {"success": False, "error": "Gemini API로부터 응답을 받지 못했습니다."}

    try:
        text = candidates[0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return {"success": False, "error": "응답 형식을 해석할 수 없습니다."}

    return {"success": True, "prompt": text}


def render_copy_button(text: str, widget_key: str):
    """클립보드 복사 버튼. iframe 내에서 navigator.clipboard 사용, 실패 시 execCommand로 대체."""
    payload = json.dumps(text)
    html_code = f"""
    <button id="{widget_key}" style="
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white; border: none; border-radius: 8px;
        padding: 8px 18px; font-size: 14px; font-weight: 600;
        cursor: pointer; font-family: sans-serif;">📋 복사하기</button>
    <script>
      const btn = document.getElementById("{widget_key}");
      const text = {payload};
      btn.addEventListener("click", async () => {{
        try {{
          await navigator.clipboard.writeText(text);
        }} catch (e) {{
          const ta = document.createElement("textarea");
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
        }}
        btn.innerText = "✅ 복사됨!";
        setTimeout(() => {{ btn.innerText = "📋 복사하기"; }}, 1500);
      }});
    </script>
    """
    st.iframe(src=html_code, height=44)


# ============================================================
# 세션 상태 초기화
# ============================================================
if "prompt_history" not in st.session_state:
    st.session_state.prompt_history = []
if "generated_prompt" not in st.session_state:
    st.session_state.generated_prompt = ""
if "generated_lang" not in st.session_state:
    st.session_state.generated_lang = "한국어"
if "current_record" not in st.session_state:
    st.session_state.current_record = None


st.title("✨ AI 프롬프트 생성기")
st.caption("요구사항을 자연어로 입력하면 Gemini AI가 최적화된 프롬프트를 자동으로 생성해드립니다.")

# ============================================================
# 사이드바 - API 키 설정
# ============================================================
with st.sidebar:
    st.markdown("### ✨ 프롬프트 생성기")
    st.caption("이 사이드바 영역은 현재 열려 있는 도구(프롬프트 생성기) 전용 설정입니다.")
    st.subheader("🔑 Gemini API 설정")

    tab_own_key, tab_password = st.tabs(["내 API 키 사용", "비밀번호로 접속"])

    api_key = ""

    with tab_own_key:
        own_key = st.text_input(
            "Gemini API Key",
            type="password",
            value=st.session_state.get("gemini_api_key", ""),
            help="Google AI Studio에서 발급받은 본인의 API 키를 입력하세요. 입력한 키는 서버에 저장되지 않고 이 세션에서만 사용됩니다.",
        )
        st.session_state.gemini_api_key = own_key
        if own_key:
            api_key = own_key

    with tab_password:
        preset_password = get_secret("APP_PASSWORD")
        entered_password = st.text_input(
            "비밀번호",
            type="password",
            help="사전에 공유받은 비밀번호를 입력하면 등록된 Gemini API 키를 사용할 수 있습니다.",
        )
        if entered_password:
            if not preset_password:
                st.error("⚠️ 비밀번호 접속 기능이 아직 설정되지 않았습니다.")
            elif entered_password != preset_password:
                st.error("❌ 비밀번호가 올바르지 않습니다.")
            else:
                preset_key = get_secret("GEMINI_API_KEY")
                if not preset_key:
                    st.error("⚠️ 등록된 API 키가 설정되지 않았습니다.")
                else:
                    api_key = preset_key
                    st.success("✅ 인증되었습니다. 등록된 API 키를 사용합니다.")

    model_label = st.selectbox("모델 선택", options=list(MODEL_OPTIONS.keys()))
    selected_model = MODEL_OPTIONS[model_label]

    st.markdown("[🔗 API 키 발급받기 (Google AI Studio)](https://aistudio.google.com/apikey)")

# ============================================================
# 입력 영역
# ============================================================
st.subheader("📝 요구사항 입력")
user_input = st.text_area(
    "어떤 결과물이 필요하신가요?",
    height=150,
    placeholder=(
        "예) 소규모 카페 창업 계획서를 작성하고 싶어. 예상 투자금, 수익 분석, 마케팅 전략이 포함되어야 해.\n"
        "예) 파이썬으로 엑셀 데이터를 자동으로 분석하고 차트를 만드는 코드가 필요해.\n"
        "예) 취업 자기소개서를 쓰고 싶은데, 성장과정과 지원동기 위주로 작성하고 싶어."
    ),
)

col1, col2 = st.columns([3, 1])
with col1:
    output_in_english = st.checkbox("🇺🇸 영문으로 출력")
with col2:
    generate_clicked = st.button("✦ 프롬프트 생성", type="primary", use_container_width=True)

if generate_clicked:
    trimmed_input = user_input.strip()
    if not api_key:
        st.error("⚠️ 사이드바에 Gemini API 키를 입력해주세요.")
    elif not trimmed_input:
        st.error("⚠️ 요구사항을 입력해주세요.")
    elif len(trimmed_input) < 5:
        st.error("⚠️ 요구사항을 좀 더 자세히 입력해주세요. (최소 5자)")
    else:
        meta_prompt = build_meta_prompt(trimmed_input, output_in_english)
        with st.spinner("Gemini AI가 최적의 프롬프트를 작성하고 있어요..."):
            try:
                result = call_gemini(api_key, selected_model, meta_prompt)
            except requests.exceptions.RequestException as e:
                result = {"success": False, "error": f"요청 중 오류가 발생했습니다: {e}"}

        if not result["success"]:
            st.error(result["error"])
        else:
            generated = result["prompt"]
            lang_label = "영문" if output_in_english else "한국어"
            record = {
                "번호": len(st.session_state.prompt_history) + 1,
                "생성 일시": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "사용자 요구사항": trimmed_input,
                "생성된 프롬프트": generated,
                "언어": lang_label,
            }
            st.session_state.generated_prompt = generated
            st.session_state.generated_lang = lang_label
            st.session_state.current_record = record
            st.session_state.prompt_history.insert(0, record)
            st.success("✅ 프롬프트가 성공적으로 생성되었습니다!")

# ============================================================
# 출력 영역
# ============================================================
st.divider()
st.subheader("💡 생성된 프롬프트")

if st.session_state.generated_prompt:
    st.code(st.session_state.generated_prompt, language=None, wrap_lines=True)
    render_copy_button(st.session_state.generated_prompt, widget_key="copy_current")

    chars = len(st.session_state.generated_prompt)
    words = len(st.session_state.generated_prompt.split())

    m1, m2, m3 = st.columns(3)
    m1.metric("글자 수", f"{chars:,}")
    m2.metric("단어 수", f"{words:,}")
    m3.metric("언어", st.session_state.generated_lang)

    if st.session_state.current_record:
        record_df = pd.DataFrame([st.session_state.current_record])
        st.download_button(
            label="📥 이 기록만 Excel로 다운로드",
            data=to_excel_bytes(record_df),
            file_name=f"프롬프트_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_current_record",
        )
else:
    st.info("요구사항을 입력하고 프롬프트 생성 버튼을 클릭하세요.")

# ============================================================
# 히스토리 영역
# ============================================================
st.divider()
st.subheader("🕐 최근 생성 기록")

if not st.session_state.prompt_history:
    st.caption("아직 생성된 프롬프트가 없습니다. 첫 번째 프롬프트를 생성해보세요! ✦")
else:
    for item in st.session_state.prompt_history[:10]:
        preview = item["사용자 요구사항"][:40]
        with st.expander(f"#{item['번호']} · {item['생성 일시']} · {item['언어']} — {preview}"):
            st.markdown(f"**요구사항:** {item['사용자 요구사항']}")
            st.code(item["생성된 프롬프트"], language=None, wrap_lines=True)
            render_copy_button(item["생성된 프롬프트"], widget_key=f"copy_hist_{item['번호']}")
            if st.button("이 프롬프트 불러오기", key=f"load_{item['번호']}"):
                st.session_state.generated_prompt = item["생성된 프롬프트"]
                st.session_state.generated_lang = item["언어"]
                st.session_state.current_record = item
                st.rerun()

    history_df = pd.DataFrame(st.session_state.prompt_history)
    st.download_button(
        label="📥 전체 기록 Excel로 다운로드",
        data=to_excel_bytes(history_df),
        file_name=f"프롬프트_기록_{datetime.date.today().isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
