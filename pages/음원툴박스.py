import asyncio
import os
import re
import tempfile

import edge_tts
import streamlit as st
import yt_dlp
from langdetect import DetectorFactory, detect

DetectorFactory.seed = 0  # 언어 감지 결과 일관성 고정

VOICE_MAP = {
    "ko": {"여성": "ko-KR-SunHiNeural", "남성": "ko-KR-InJoonNeural"},
    "en": {"여성": "en-US-AvaNeural", "남성": "en-US-GuyNeural"},
}

INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_filename(name: str) -> str:
    name = re.sub(r"\.mp3$", "", name.strip(), flags=re.IGNORECASE)
    return INVALID_FILENAME_CHARS.sub("_", name)


async def synthesize_speech(text: str, voice: str, out_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


st.title("🎧 음원 툴박스")
st.caption("유튜브 영상을 MP3로 추출하거나, 텍스트를 음성(TTS)으로 변환합니다.")

tab_youtube, tab_tts = st.tabs(["🎵 유튜브 MP3 추출", "🎤 텍스트 음성 변환 (TTS)"])

# ============================================================
# 세션 상태 초기화
# ============================================================
if "yt_audio_bytes" not in st.session_state:
    st.session_state.yt_audio_bytes = None
if "yt_audio_filename" not in st.session_state:
    st.session_state.yt_audio_filename = None
if "tts_audio_bytes" not in st.session_state:
    st.session_state.tts_audio_bytes = None
if "tts_audio_filename" not in st.session_state:
    st.session_state.tts_audio_filename = None

# ============================================================
# 탭 1: 유튜브 MP3 추출
# ============================================================
with tab_youtube:
    st.subheader("유튜브 URL → MP3")

    yt_url = st.text_input("유튜브 URL", placeholder="https://www.youtube.com/watch?v=...")
    yt_filename = st.text_input(
        "저장할 파일 이름 (선택, 비우면 영상 제목 사용)",
        placeholder="예: 좋아하는노래",
        key="yt_filename_input",
    )
    yt_clicked = st.button("⬇️ MP3로 추출", type="primary", key="yt_extract_btn")

    if yt_clicked:
        if not yt_url.strip():
            st.error("⚠️ 유튜브 URL을 입력해주세요.")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                if yt_filename.strip():
                    out_tmpl = os.path.join(tmpdir, f"{sanitize_filename(yt_filename)}.%(ext)s")
                else:
                    out_tmpl = os.path.join(tmpdir, "%(title)s.%(ext)s")

                ydl_opts = {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                    "outtmpl": out_tmpl,
                    "quiet": True,
                    "no_warnings": True,
                }

                try:
                    with st.spinner("유튜브에서 오디오를 추출하는 중입니다..."):
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([yt_url])

                    mp3_files = [f for f in os.listdir(tmpdir) if f.lower().endswith(".mp3")]
                    if not mp3_files:
                        st.error("❌ MP3 파일 생성에 실패했습니다. URL을 확인해주세요.")
                    else:
                        mp3_path = os.path.join(tmpdir, mp3_files[0])
                        with open(mp3_path, "rb") as f:
                            st.session_state.yt_audio_bytes = f.read()
                        st.session_state.yt_audio_filename = mp3_files[0]
                        st.success(f"✅ 추출 완료: {mp3_files[0]}")
                except Exception as e:
                    st.error(f"❌ 에러가 발생했습니다: {e}")

    if st.session_state.yt_audio_bytes:
        st.audio(st.session_state.yt_audio_bytes, format="audio/mp3")
        st.download_button(
            label="📥 MP3 파일 다운로드",
            data=st.session_state.yt_audio_bytes,
            file_name=st.session_state.yt_audio_filename,
            mime="audio/mpeg",
            key="yt_download_btn",
        )

# ============================================================
# 탭 2: TTS (텍스트 → 음성)
# ============================================================
with tab_tts:
    st.subheader("텍스트 → 음성 (MP3)")

    input_mode = st.radio("입력 방식을 선택하세요:", ("직접 입력", "파일 업로드 (txt)"), horizontal=True)

    tts_text = ""
    if input_mode == "직접 입력":
        tts_text = st.text_area(
            "변환할 내용을 입력하세요:",
            placeholder="여기에 음성으로 변환할 텍스트를 입력하세요...",
            height=200,
        ).strip()
    else:
        uploaded_file = st.file_uploader("텍스트 파일(.txt)을 선택하세요:", type=["txt"])
        if uploaded_file is not None:
            try:
                tts_text = uploaded_file.read().decode("utf-8").strip()
                st.success("파일을 성공적으로 불러왔습니다!")
                with st.expander("파일 내용 보기"):
                    st.text(tts_text)
            except Exception as e:
                st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

    detected_lang = "ko"
    if tts_text:
        try:
            detected_lang = detect(tts_text[:100])
            st.info(f"🔍 감지된 언어: **{detected_lang.upper()}**")
        except Exception:
            detected_lang = "ko"
            st.warning("⚠️ 언어 감지에 실패하여 기본값(한국어)으로 설정합니다.")

    gender_choice = st.selectbox("목소리 성별을 선택하세요:", options=["여성", "남성"], index=0)
    target_lang = detected_lang if detected_lang in VOICE_MAP else "ko"
    selected_voice = VOICE_MAP[target_lang][gender_choice]

    tts_filename = st.text_input("저장할 파일 이름 (선택사항):", placeholder="output.mp3", key="tts_filename_input")

    if st.button("🔊 음성 생성하기", type="primary", key="tts_generate_btn"):
        if not tts_text:
            st.error("❌ 변환할 내용이 없습니다. 텍스트를 입력하거나 파일을 업로드해 주세요.")
        else:
            output_name = sanitize_filename(tts_filename) if tts_filename.strip() else "output"
            output_name += ".mp3"

            with tempfile.TemporaryDirectory() as tmpdir:
                out_path = os.path.join(tmpdir, output_name)
                with st.spinner("⚡ 음성을 생성하고 있습니다. 잠시만 기다려 주세요..."):
                    try:
                        asyncio.run(synthesize_speech(tts_text, selected_voice, out_path))
                        with open(out_path, "rb") as f:
                            st.session_state.tts_audio_bytes = f.read()
                        st.session_state.tts_audio_filename = output_name
                        st.success("✅ 음성 변환이 완료되었습니다!")
                    except Exception as e:
                        st.error(f"❌ 에러 발생: {e}")

    if st.session_state.tts_audio_bytes:
        st.audio(st.session_state.tts_audio_bytes, format="audio/mp3")
        st.download_button(
            label="📥 MP3 파일 다운로드",
            data=st.session_state.tts_audio_bytes,
            file_name=st.session_state.tts_audio_filename,
            mime="audio/mpeg",
            key="tts_download_btn",
        )
