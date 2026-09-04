import io
import zipfile

import pandas as pd
import pymupdf
import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates

ZOOM = 1.4
# PyMuPDF 내장 한글(CJK) 폰트 - 별도 폰트 파일 없이 동작하므로 배포 환경(Linux 등)에서도 안전
KOREAN_FONT = "korea-s"


def sanitize_filename(name: str) -> str:
    for ch in '\\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


@st.cache_data(show_spinner=False)
def get_page_count(pdf_bytes: bytes) -> int:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    n = len(doc)
    doc.close()
    return n


@st.cache_data(show_spinner=False)
def render_page_png(pdf_bytes: bytes, page_num: int, zoom: float) -> bytes:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    doc.close()
    return pix.tobytes("png")


def build_preview_image(base_png: bytes, mappings: list, sample_row: pd.Series, page_num: int, zoom: float) -> Image.Image:
    img = Image.open(io.BytesIO(base_png)).convert("RGB")
    draw = ImageDraw.Draw(img)
    for m in mappings:
        if m["page"] != page_num:
            continue
        col = m["column"]
        val = sample_row.get(col, "") if sample_row is not None else ""
        text = "" if pd.isna(val) else str(val)
        sx, sy = m["pdf_x"] * zoom, m["pdf_y"] * zoom
        r = 4
        draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill="red")
        draw.text((sx + 8, sy - 14), f"[{col} {m['font_size']}pt]", fill=(0, 80, 180))
        if text:
            draw.text((sx, sy + 4), text, fill=(200, 30, 30))
    return img


def generate_pdfs(template_bytes: bytes, df: pd.DataFrame, mappings: list, prefix: str, fname_col: str | None):
    zip_buffer = io.BytesIO()
    success = 0
    errors = []
    used_names = set()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, row in df.iterrows():
            try:
                doc = pymupdf.open(stream=template_bytes, filetype="pdf")

                for m in mappings:
                    col = m["column"]
                    if col not in df.columns:
                        continue
                    val = row[col]
                    text = "" if pd.isna(val) else str(val)
                    if not text:
                        continue
                    page_num = m["page"]
                    if page_num >= len(doc):
                        continue

                    fs = m["font_size"]
                    doc[page_num].insert_text(
                        (m["pdf_x"], m["pdf_y"] + fs),
                        text,
                        fontname=KOREAN_FONT,
                        fontsize=fs,
                        color=(0, 0, 0),
                    )

                if fname_col and fname_col in df.columns:
                    fname_val = row[fname_col]
                    fname_val = "" if pd.isna(fname_val) else str(fname_val)
                else:
                    fname_val = ""
                if not fname_val:
                    fname_val = str(i + 1)

                sep = "_" if prefix and fname_val else ""
                base_name = sanitize_filename(f"{prefix}{sep}{fname_val}") or str(i + 1)

                final_name = f"{base_name}.pdf"
                dup_idx = 1
                while final_name in used_names:
                    dup_idx += 1
                    final_name = f"{base_name}_{dup_idx}.pdf"
                used_names.add(final_name)

                zf.writestr(final_name, doc.tobytes())
                doc.close()
                success += 1
            except Exception as e:
                errors.append(f"행 {i + 1}: {e}")

    zip_buffer.seek(0)
    return zip_buffer.getvalue(), success, errors


# ============================================================
# 세션 상태 초기화
# ============================================================
if "form_mappings" not in st.session_state:
    st.session_state.form_mappings = []
if "form_template_sig" not in st.session_state:
    st.session_state.form_template_sig = None
if "form_last_click_time" not in st.session_state:
    st.session_state.form_last_click_time = None
if "form_result_zip" not in st.session_state:
    st.session_state.form_result_zip = None


st.title("📄 대량 양식 생성기")
st.caption("PDF 양식의 원하는 위치에 엑셀 데이터를 자동으로 채워, 행 개수만큼의 개별 PDF를 한 번에 생성합니다. (예: 100명의 연봉계약서)")

# ============================================================
# 1단계: 업로드
# ============================================================
st.subheader("1단계: 템플릿 업로드")
col_up1, col_up2 = st.columns(2)
with col_up1:
    template_file = st.file_uploader("PDF 양식 템플릿", type=["pdf"], key="template_upload")
with col_up2:
    excel_file = st.file_uploader("데이터 Excel 파일 (한 행 = 한 개의 문서)", type=["xlsx", "xls"], key="excel_upload")

if template_file is not None and excel_file is not None:
    template_bytes = template_file.getvalue()
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        st.error(f"❌ 엑셀 파일을 읽을 수 없습니다: {e}")
        st.stop()

    if df.empty or len(df.columns) == 0:
        st.error("❌ 엑셀 파일에 데이터가 없습니다.")
        st.stop()

    # 새 템플릿이 업로드되면 기존 위치 설정 초기화
    template_sig = f"{template_file.name}_{template_file.size}_{excel_file.name}_{excel_file.size}"
    if st.session_state.form_template_sig != template_sig:
        st.session_state.form_template_sig = template_sig
        st.session_state.form_mappings = []
        st.session_state.form_last_click_time = None
        st.session_state.form_result_zip = None

    try:
        page_count = get_page_count(template_bytes)
    except Exception as e:
        st.error(f"❌ PDF 파일을 읽을 수 없습니다: {e}")
        st.stop()

    # ============================================================
    # 2단계: 삽입 위치 지정
    # ============================================================
    st.divider()
    st.subheader("2단계: 삽입 위치 지정")
    st.caption("항목·글자크기를 고른 뒤 아래 PDF 미리보기를 클릭하면 그 위치에 값이 삽입됩니다.")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        target_col = st.selectbox("삽입할 항목 (엑셀 열)", options=list(df.columns), key="target_col_select")
    with col_b:
        font_size = st.number_input("글자 크기", min_value=6, max_value=72, value=12, key="font_size_input")
    with col_c:
        if page_count > 1:
            page_num_ui = st.number_input("페이지", min_value=1, max_value=page_count, value=1, key="page_num_input")
        else:
            page_num_ui = 1
            st.caption("페이지 1 / 1")
    page_idx = int(page_num_ui) - 1

    base_png = render_page_png(template_bytes, page_idx, ZOOM)
    preview_img = build_preview_image(base_png, st.session_state.form_mappings, df.iloc[0], page_idx, ZOOM)

    coords = streamlit_image_coordinates(preview_img, key=f"pdf_click_area_{page_idx}")

    if coords is not None and coords.get("unix_time") != st.session_state.form_last_click_time:
        st.session_state.form_last_click_time = coords["unix_time"]
        pdf_x = round(coords["x"] / ZOOM, 2)
        pdf_y = round(coords["y"] / ZOOM, 2)
        st.session_state.form_mappings.append(
            {
                "column": target_col,
                "page": page_idx,
                "pdf_x": pdf_x,
                "pdf_y": pdf_y,
                "font_size": int(font_size),
            }
        )
        st.rerun()

    st.markdown("**추가된 위치**")
    if st.session_state.form_mappings:
        for idx, m in enumerate(st.session_state.form_mappings):
            row_col1, row_col2 = st.columns([6, 1])
            with row_col1:
                page_label = f"p{m['page'] + 1} · " if page_count > 1 else ""
                st.write(f"{page_label}**{m['column']}** — 위치({m['pdf_x']}, {m['pdf_y']}), {m['font_size']}pt")
            with row_col2:
                if st.button("삭제", key=f"del_mapping_{idx}"):
                    st.session_state.form_mappings.pop(idx)
                    st.rerun()
        if st.button("전체 초기화", key="clear_all_mappings"):
            st.session_state.form_mappings = []
            st.rerun()
    else:
        st.caption("아직 지정된 위치가 없습니다.")

    # ============================================================
    # 3단계: 파일명 규칙
    # ============================================================
    st.divider()
    st.subheader("3단계: 파일명 규칙")
    fc1, fc2 = st.columns(2)
    with fc1:
        filename_prefix = st.text_input("파일명 접두사 (선택)", placeholder="예: 연봉계약서", key="filename_prefix_input")
    with fc2:
        filename_column = st.selectbox(
            "파일명에 사용할 열 (선택 안 하면 순번 사용)",
            options=["(사용 안 함)"] + list(df.columns),
            key="filename_column_select",
        )
    fname_col_value = None if filename_column == "(사용 안 함)" else filename_column

    sample_sep = "_" if filename_prefix and fname_col_value else ""
    sample_suffix = f"{{{fname_col_value}}}" if fname_col_value else "{순번}"
    st.caption(f"예시 파일명: {filename_prefix}{sample_sep}{sample_suffix}.pdf")

    # ============================================================
    # 4단계: 생성
    # ============================================================
    st.divider()
    st.subheader("4단계: PDF 일괄 생성")
    st.write(f"엑셀 {len(df)}행 → PDF {len(df)}개가 생성됩니다.")

    if st.button("📄 PDF 일괄 생성", type="primary", key="generate_pdfs_btn"):
        if not st.session_state.form_mappings:
            st.error("⚠️ 삽입 위치를 최소 1개 이상 지정해주세요.")
        else:
            with st.spinner("PDF를 생성하는 중입니다..."):
                zip_bytes, success, errors = generate_pdfs(
                    template_bytes, df, st.session_state.form_mappings, filename_prefix, fname_col_value
                )
            st.session_state.form_result_zip = zip_bytes
            st.success(f"✅ {success}개 PDF 생성 완료 (전체 {len(df)}행 중)")
            if errors:
                st.warning(f"⚠️ 오류 {len(errors)}건")
                for err in errors[:5]:
                    st.error(err)

    if st.session_state.form_result_zip:
        st.download_button(
            label="📥 전체 PDF ZIP 다운로드",
            data=st.session_state.form_result_zip,
            file_name="생성된_양식.zip",
            mime="application/zip",
            key="download_zip_btn",
        )
else:
    st.info("PDF 양식 템플릿과 데이터 Excel 파일을 모두 업로드하면 다음 단계가 나타납니다.")
