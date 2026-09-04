# -*- coding: utf-8 -*-

import io

import pandas as pd
import streamlit as st

st.title("🧹 데이터 클렌징 & 병합")
st.write(
    "엑셀 데이터에서 불필요한 행/열을 제거하고, 조건에 맞는 행을 필터링하거나 "
    "다른 엑셀 파일과 병합한 뒤 결과를 다운로드할 수 있는 도구입니다. "
    "각 단계는 '적용' 버튼을 눌러야 반영됩니다."
)


@st.cache_data(show_spinner=False)
def load_excel(file_bytes: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(file_bytes))


@st.cache_data(show_spinner=False)
def load_excel_no_header(file_bytes: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(file_bytes), header=None)


@st.cache_data(show_spinner=False)
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="cleaned_data")
    return buffer.getvalue()


def apply_trim_and_header(base_df, top_n, bottom_n, left_n, right_n):
    """상/하/좌/우 트림을 적용하고, 상단 행을 제거한 경우 새로 맨 위로 온 행을 열 이름으로 승격."""
    messages = []
    df = base_df

    start_row, end_row = int(top_n), len(df) - int(bottom_n)
    if (top_n > 0 or bottom_n > 0) and start_row >= end_row:
        messages.append(("warning", "⚠️ 제거할 행 수가 전체 행 수보다 많거나 같아 행 제거를 건너뜁니다."))
    else:
        df = df.iloc[start_row:end_row, :]

        if top_n > 0:
            if df.empty:
                messages.append(
                    ("warning", "⚠️ 상단 행 제거 후 남은 데이터가 없어 열 이름을 다시 지정할 수 없습니다.")
                )
            else:
                new_header = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)

                new_columns = []
                seen_names = {}
                for i, c in enumerate(new_header):
                    name = str(c).strip() if pd.notna(c) and str(c).strip() else f"열_{i + 1}"
                    if name in seen_names:
                        seen_names[name] += 1
                        name = f"{name}_{seen_names[name]}"
                    else:
                        seen_names[name] = 0
                    new_columns.append(name)
                df.columns = new_columns

                messages.append(("info", "ℹ️ 상단 행 제거 후 남은 첫 번째 행을 새 열 이름으로 사용했습니다."))

    start_col, end_col = int(left_n), len(df.columns) - int(right_n)
    if (left_n > 0 or right_n > 0) and start_col >= end_col:
        messages.append(("warning", "⚠️ 제거할 열 수가 전체 열 수보다 많거나 같아 열 제거를 건너뜁니다."))
    else:
        df = df.iloc[:, start_col:end_col]

    return df, messages


def get_current_df(up_to_step: int) -> pd.DataFrame:
    """up_to_step까지 적용된 스냅샷 중 가장 마지막 것을 반환 (없으면 이전 단계로 거슬러 올라감)."""
    for k in range(up_to_step, 0, -1):
        key = f"snap{k}"
        if key in st.session_state:
            return st.session_state[key]
    return st.session_state.snap1


def invalidate_downstream(from_step: int):
    """from_step 이후의 스냅샷을 모두 제거 (상류 단계가 다시 적용되어 하류가 낡은 경우)."""
    for k in range(from_step, 6):
        st.session_state.pop(f"snap{k}", None)
    # 상류가 바뀌면 이미 준비해 둔 다운로드 파일도 낡은 것이므로 함께 무효화
    st.session_state.pop("export_bytes", None)
    st.session_state.pop("export_name", None)


def show_messages(messages):
    for level, text in messages:
        getattr(st, level)(text)


# ---------------------------------------------------------
# 2. 1단계: 원본 엑셀 파일 업로드
# ---------------------------------------------------------
st.subheader("1️⃣ 원본 엑셀 파일 업로드")
main_file = st.file_uploader(
    "메인 엑셀 파일(.xlsx, .xls)을 업로드하세요", type=["xlsx", "xls"], key="main_file"
)

if main_file is None:
    st.info("먼저 엑셀 파일을 업로드해주세요.")
    st.stop()

file_signature = f"{main_file.name}_{main_file.size}"
if st.session_state.get("main_file_signature") != file_signature:
    try:
        st.session_state.snap1 = load_excel(main_file.getvalue())
    except Exception as e:
        st.error(f"엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")
        st.stop()
    st.session_state.main_file_signature = file_signature
    invalidate_downstream(2)

snap1 = st.session_state.snap1
st.caption(f"원본 데이터 형태: {snap1.shape[0]}행 × {snap1.shape[1]}열")
with st.expander("원본 데이터 미리보기"):
    st.dataframe(snap1.head(20), use_container_width=True)

# ---------------------------------------------------------
# 3. 2단계: 상/하/좌/우 불필요한 행·열 제거
# ---------------------------------------------------------
st.divider()
st.subheader("2️⃣ 상/하/좌/우 불필요한 행·열 제거")

base2 = get_current_df(1)
st.caption(f"이 단계에 입력되는 데이터: {base2.shape[0]}행 × {base2.shape[1]}열")

c1, c2, c3, c4 = st.columns(4)
with c1:
    top_n = st.number_input("상단에서 제거할 행 수", min_value=0, value=0, step=1)
with c2:
    bottom_n = st.number_input("하단에서 제거할 행 수", min_value=0, value=0, step=1)
with c3:
    left_n = st.number_input("좌측에서 제거할 열 수", min_value=0, value=0, step=1)
with c4:
    right_n = st.number_input("우측에서 제거할 열 수", min_value=0, value=0, step=1)

if st.button("2단계 적용", type="primary", key="apply_step2"):
    result_df, messages = apply_trim_and_header(base2, top_n, bottom_n, left_n, right_n)
    st.session_state.snap2 = result_df
    invalidate_downstream(3)
    show_messages(messages)
    st.success(
        f"✅ 2단계 적용 완료: {base2.shape[0]}행×{base2.shape[1]}열 → "
        f"{result_df.shape[0]}행×{result_df.shape[1]}열"
    )

df2 = get_current_df(2)
st.caption(f"현재 데이터 형태(2단계까지 반영): {df2.shape[0]}행 × {df2.shape[1]}열")

# ---------------------------------------------------------
# 4. 3단계: 특정 열 제거 또는 유지
# ---------------------------------------------------------
st.divider()
st.subheader("3️⃣ 특정 열 제거 또는 유지")

base3 = get_current_df(2)
st.caption(f"이 단계에 입력되는 데이터: {base3.shape[0]}행 × {base3.shape[1]}열")

col_mode = st.radio(
    "열 처리 방식",
    options=["건너뛰기", "제거할 열 선택", "남길 열 선택"],
    horizontal=True,
)

cols_to_remove = []
cols_to_keep = []
if col_mode == "제거할 열 선택":
    cols_to_remove = st.multiselect("제거할 열을 선택하세요", options=list(base3.columns))
elif col_mode == "남길 열 선택":
    cols_to_keep = st.multiselect("남길 열을 선택하세요", options=list(base3.columns))

if st.button("3단계 적용", type="primary", key="apply_step3"):
    result_df = base3
    if col_mode == "제거할 열 선택" and cols_to_remove:
        if len(cols_to_remove) == len(base3.columns):
            st.warning("⚠️ 모든 열을 제거하도록 선택되어 있어 적용하지 않습니다. 선택을 조정해주세요.")
        else:
            result_df = base3.drop(columns=cols_to_remove)
    elif col_mode == "남길 열 선택" and cols_to_keep:
        result_df = base3[cols_to_keep]

    st.session_state.snap3 = result_df
    invalidate_downstream(4)
    st.success(
        f"✅ 3단계 적용 완료: {base3.shape[0]}행×{base3.shape[1]}열 → "
        f"{result_df.shape[0]}행×{result_df.shape[1]}열"
    )

df3 = get_current_df(3)
st.caption(f"현재 데이터 형태(3단계까지 반영): {df3.shape[0]}행 × {df3.shape[1]}열")

# ---------------------------------------------------------
# 5. 4단계: 특정 열 값 기준으로 행 제거
# ---------------------------------------------------------
st.divider()
st.subheader("4️⃣ 특정 열 값 기준으로 행 제거")

base4 = get_current_df(3)
st.caption(f"이 단계에 입력되는 데이터: {base4.shape[0]}행 × {base4.shape[1]}열")

if base4.empty or len(base4.columns) == 0:
    st.info("현재 데이터가 비어 있어 이 단계를 건너뜁니다.")
else:
    target_cols = st.multiselect(
        "행을 제거할 기준 열 (여러 개 선택 가능)", options=list(base4.columns)
    )

    col_filters = {}  # 열 이름 -> 제거할 값 목록
    if target_cols:
        for group_start in range(0, len(target_cols), 4):
            group = target_cols[group_start : group_start + 4]
            group_widgets = st.columns(len(group))
            for widget, col_name in zip(group_widgets, group):
                with widget:
                    st.markdown(f"**{col_name}**")
                    method = st.radio(
                        "입력 방식",
                        options=["직접 입력", "엑셀 파일"],
                        key=f"remove_method_{col_name}",
                    )

                    values = []
                    if method == "직접 입력":
                        values_str = st.text_area(
                            "제거할 값 (쉼표 구분)",
                            key=f"remove_values_{col_name}",
                            height=100,
                        )
                        values = [v.strip() for v in values_str.split(",") if v.strip()]
                    else:
                        remove_file = st.file_uploader(
                            "엑셀 파일 (A열, 헤더 없음)",
                            type=["xlsx", "xls"],
                            key=f"remove_file_{col_name}",
                        )
                        if remove_file is not None:
                            try:
                                df_remove = load_excel_no_header(remove_file.getvalue())
                                if not df_remove.empty:
                                    values = df_remove.iloc[:, 0].dropna().astype(str).tolist()
                                else:
                                    st.warning("⚠️ 파일이 비어 있습니다.")
                            except Exception as e:
                                st.error(f"파일 읽기 오류: {e}")

                    col_filters[col_name] = values

    if st.button("4단계 적용", type="primary", key="apply_step4"):
        result_df = base4
        applied_cols = [c for c in target_cols if col_filters.get(c)]

        if applied_cols:
            mask = pd.Series(False, index=base4.index)
            for col_name in applied_cols:
                mask = mask | base4[col_name].astype(str).isin(col_filters[col_name])
            result_df = base4[~mask]

        st.session_state.snap4 = result_df
        invalidate_downstream(5)

        if not target_cols:
            st.success("✅ 4단계 적용 완료: 기준 열을 선택하지 않아 변경 없이 진행합니다.")
        elif not applied_cols:
            st.success("✅ 4단계 적용 완료: 제거할 값이 없어 변경 없이 진행합니다.")
        else:
            removed = len(base4) - len(result_df)
            st.success(
                f"✅ 4단계 적용 완료: {', '.join(applied_cols)} 기준으로 {removed}개 행을 제거했습니다 "
                f"({base4.shape[0]}행×{base4.shape[1]}열 → {result_df.shape[0]}행×{result_df.shape[1]}열)"
            )

df4 = get_current_df(4)
st.caption(f"현재 데이터 형태(4단계까지 반영): {df4.shape[0]}행 × {df4.shape[1]}열")

# ---------------------------------------------------------
# 6. 5단계: 다른 엑셀 파일과 병합 (Left Merge)
# ---------------------------------------------------------
st.divider()
st.subheader("5️⃣ 다른 엑셀 파일과 병합 (Left Merge)")

base5 = get_current_df(4)
st.caption(f"이 단계에 입력되는 데이터: {base5.shape[0]}행 × {base5.shape[1]}열")

do_merge = st.checkbox("다른 엑셀 파일과 병합하기")
df_merge = None
main_key = None
merge_key = None
if do_merge:
    merge_file = st.file_uploader(
        "병합할 엑셀 파일(.xlsx, .xls)", type=["xlsx", "xls"], key="merge_file"
    )
    if merge_file is not None:
        try:
            df_merge = load_excel(merge_file.getvalue())
            st.caption(f"병합할 데이터 형태: {df_merge.shape[0]}행 × {df_merge.shape[1]}열")
        except Exception as e:
            st.error(f"병합할 엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")
            df_merge = None

        if df_merge is not None:
            mc1, mc2 = st.columns(2)
            with mc1:
                main_key = st.selectbox("메인 데이터의 기준 열 (Key)", options=list(base5.columns))
            with mc2:
                merge_key = st.selectbox(
                    "병합할 데이터의 기준 열 (Key)", options=list(df_merge.columns)
                )

if st.button("5단계 적용", type="primary", key="apply_step5"):
    result_df = base5
    if do_merge and df_merge is not None and main_key and merge_key:
        try:
            result_df = pd.merge(base5, df_merge, how="left", left_on=main_key, right_on=merge_key)
            # 병합할 데이터의 키 열 이름이 메인 데이터와 다르면, 메인 쪽 키에 이미
            # 동일한 정보가 있으므로 병합된 결과에서는 그 키 열을 제외 (다른 정보만 붙임)
            if merge_key != main_key and merge_key in result_df.columns:
                result_df = result_df.drop(columns=[merge_key])
            st.success(
                f"✅ 5단계 적용 완료: 병합 후 {base5.shape[0]}행×{base5.shape[1]}열 → "
                f"{result_df.shape[0]}행×{result_df.shape[1]}열"
            )
        except Exception as e:
            st.error(f"병합 중 오류가 발생했습니다: {e}")
            result_df = base5
    else:
        st.success("✅ 5단계 적용 완료: 병합을 사용하지 않아 변경 없이 진행합니다.")

    st.session_state.snap5 = result_df
    invalidate_downstream(6)

df5 = get_current_df(5)
st.caption(f"현재 데이터 형태(5단계까지 반영): {df5.shape[0]}행 × {df5.shape[1]}열")

# ---------------------------------------------------------
# 7. 6단계: 결과 확인 및 다운로드
# ---------------------------------------------------------
st.divider()
st.subheader("6️⃣ 결과 확인 및 다운로드")

final_df = get_current_df(5)

if final_df.empty:
    st.warning("⚠️ 최종 데이터가 비어 있어 다운로드할 내용이 없습니다.")
else:
    st.success(f"✅ 최종 데이터: {final_df.shape[0]}행 × {final_df.shape[1]}열")
    st.dataframe(final_df, use_container_width=True)

    default_name = main_file.name
    if not default_name.lower().endswith((".xlsx", ".xls")):
        default_name += ".xlsx"
    default_name = f"cleaned_{default_name}"

    output_name = st.text_input("저장할 파일 이름", value=default_name)
    if not output_name.lower().endswith((".xlsx", ".xls")):
        output_name += ".xlsx"

    if st.button("💾 저장하기", type="primary", key="prepare_save"):
        with st.spinner("Excel 파일을 생성하는 중입니다..."):
            st.session_state.export_bytes = to_excel_bytes(final_df)
            st.session_state.export_name = output_name
        st.success(
            f"✅ 저장 준비 완료: {output_name} "
            f"({len(st.session_state.export_bytes) / 1024:.1f} KB). "
            "아래 다운로드 버튼을 눌러 파일을 받으세요."
        )

    if "export_bytes" in st.session_state:
        st.download_button(
            label=f"📥 Excel 파일 다운로드 ({st.session_state.export_name})",
            data=st.session_state.export_bytes,
            file_name=st.session_state.export_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
