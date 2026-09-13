import io
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageOps
from streamlit_image_coordinates import streamlit_image_coordinates

MAX_DISPLAY_WIDTH = 700
POINT_LABELS = ["① 좌상단", "② 우상단", "③ 우하단", "④ 좌하단"]
MARKER_COLOR = (255, 0, 255)

st.title("📐 문서스캔변환기")
st.caption("비스듬하게 찍힌 서류 사진에서 4개의 꼭짓점을 순서대로(좌상단→우상단→우하단→좌하단) 클릭하면 반듯한 사각형 이미지로 보정합니다.")

uploaded = st.file_uploader("보정할 서류 사진을 업로드하세요", type=["png", "jpg", "jpeg", "bmp", "tiff"])

if uploaded is None:
    st.info("사진을 업로드하면 꼭짓점을 클릭할 수 있는 화면이 나타납니다.")
    st.stop()

# 새 파일이 업로드되면 이전 사진에서 찍었던 점을 초기화한다.
file_id = f"{uploaded.name}_{uploaded.size}"
if st.session_state.get("scan_file_id") != file_id:
    st.session_state.scan_file_id = file_id
    st.session_state.scan_points = []
    st.session_state.scan_last_click_time = None

# 휴대폰 카메라 사진은 EXIF 방향 정보가 따로 저장되는 경우가 많아, 그대로 열면
# 화면에는 옆으로 눕거나 뒤집힌 채로 표시될 수 있어 방향을 먼저 바로잡는다.
original_img = ImageOps.exif_transpose(Image.open(uploaded).convert("RGB"))
orig_w, orig_h = original_img.size

# 클릭 좌표를 정확히 잡을 수 있으면서도 화면에 다 들어오도록 축소본을 보여주고,
# 실제 변환은 원본 해상도 그대로 수행해 결과 화질을 유지한다.
scale = min(1.0, MAX_DISPLAY_WIDTH / orig_w)
display_img = original_img.resize((int(orig_w * scale), int(orig_h * scale))) if scale < 1.0 else original_img.copy()

points = st.session_state.scan_points

if len(points) < 4:
    st.write(f"**{POINT_LABELS[len(points)]}** 을(를) 클릭하세요. ({len(points)}/4)")
else:
    st.success("✅ 4개 꼭짓점을 모두 선택했습니다. 아래에서 결과를 확인하세요.")

preview = display_img.copy()
draw = ImageDraw.Draw(preview)
disp_points = [(x * scale, y * scale) for x, y in points]
for i, (dx, dy) in enumerate(disp_points):
    r = 6
    draw.ellipse([dx - r, dy - r, dx + r, dy + r], fill=MARKER_COLOR)
    draw.text((dx + 8, dy - 10), str(i + 1), fill=MARKER_COLOR)
line_points = disp_points + [disp_points[0]] if len(disp_points) == 4 else disp_points
if len(line_points) > 1:
    draw.line(line_points, fill=MARKER_COLOR, width=2)

coords = streamlit_image_coordinates(preview, key=f"scan_click_{file_id}")

if coords is not None and coords.get("unix_time") != st.session_state.scan_last_click_time:
    st.session_state.scan_last_click_time = coords["unix_time"]
    if len(points) < 4:
        points.append((coords["x"] / scale, coords["y"] / scale))
        st.rerun()

if st.button("↺ 초기화 (다시 찍기)"):
    st.session_state.scan_points = []
    st.rerun()

if len(points) == 4:
    st.divider()
    st.subheader("⚙️ 출력 설정")

    pts = np.array(points, dtype=np.float32)
    tl, tr, br, bl = pts
    # 사각형 네 변의 길이를 재서 문서의 실제 가로/세로 비율에 가까운 크기를 기본값으로 제안한다.
    auto_width = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    auto_height = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))

    fmt_col, size_col = st.columns(2)
    with fmt_col:
        output_format = st.selectbox("저장 형식", ["png", "jpg", "pdf"])
    with size_col:
        size_mode = st.radio("크기", ["자동(추정 크기)", "A4"], horizontal=True) if output_format == "pdf" else "자동(추정 크기)"

    if size_mode == "A4":
        out_width, out_height = 2480, 3508
    else:
        w_col, h_col = st.columns(2)
        out_width = int(w_col.number_input("가로(px)", min_value=50, value=max(auto_width, 50), step=10))
        out_height = int(h_col.number_input("세로(px)", min_value=50, value=max(auto_height, 50), step=10))

    dst = np.array([[0, 0], [out_width, 0], [out_width, out_height], [0, out_height]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(pts, dst)
    src_bgr = cv2.cvtColor(np.array(original_img), cv2.COLOR_RGB2BGR)
    result_bgr = cv2.warpPerspective(src_bgr, matrix, (out_width, out_height))
    result_img = Image.fromarray(cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB))

    st.image(result_img, caption="보정 결과", use_container_width=True)

    stem = Path(uploaded.name).stem
    buffer = io.BytesIO()
    if output_format == "png":
        result_img.save(buffer, format="PNG")
        mime, file_name = "image/png", f"{stem}_보정.png"
    elif output_format == "jpg":
        result_img.save(buffer, format="JPEG", quality=95)
        mime, file_name = "image/jpeg", f"{stem}_보정.jpg"
    else:
        resolution = 300.0 if size_mode == "A4" else 100.0
        result_img.save(buffer, format="PDF", resolution=resolution)
        mime, file_name = "application/pdf", f"{stem}_보정.pdf"

    st.download_button("📥 보정된 파일 다운로드", data=buffer.getvalue(), file_name=file_name, mime=mime)
