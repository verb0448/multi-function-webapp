# -*- coding: utf-8 -*-

import io
import random
import string
import uuid

import pandas as pd
import streamlit as st
from faker import Faker

st.title("🎭 가상데이터생성기")
st.write(
    "AI 모델 학습 등에 실제 개인정보 대신 사용할 수 있는 **가상(Fake) Data**를 "
    "손쉽게 생성하고 Excel 파일로 다운로드할 수 있는 도구입니다."
)

# ---------------------------------------------------------
# 2. Faker 인스턴스 초기화 (한국 로케일)
# ---------------------------------------------------------
fake = Faker("ko_KR")

# ---------------------------------------------------------
# 3. 고정 항목 정의
#    - SIMPLE_FIELD_MAP: faker 메서드를 인자 없이 바로 호출하는 항목
#    - CALC_FIELD_MAP: faker 인스턴스를 받아 값을 계산하는 항목 (범위 지정 등)
# ---------------------------------------------------------
SIMPLE_FIELD_MAP = {
    "이름": "name",
    "주민등록번호": "ssn",
    "생년월일": "date_of_birth",
    "전화번호": "phone_number",
    "이메일": "email",
    "주소": "address",
    "직업": "job",
    "회사": "company",
    "아이디": "user_name",
    "신용카드번호": "credit_card_number",
    "신용카드사": "credit_card_provider",
    "카드 유효기간": "credit_card_expire",
    "접속 IP": "ipv4",
}

CALC_FIELD_MAP = {
    "성별": lambda f: f.random_element(elements=("남", "여")),
    "연소득": lambda f: f.random_int(min=2000, max=15000) * 10000,
    "월보험료": lambda f: f.random_int(min=1, max=50) * 10000,
    "가입일": lambda f: f.date_between(start_date="-5y", end_date="today"),
    # Faker에 blood_group 메서드가 없어 직접 목록에서 무작위 선택
    "혈액형": lambda f: f.random_element(
        elements=("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
    ),
}

# 표시 순서 (multiselect 클릭 순서와 무관하게 항상 이 순서로 컬럼을 생성)
ALL_FIELD_LABELS = [
    "이름", "주민등록번호", "성별", "생년월일", "전화번호", "이메일", "주소", "직업", "회사",
    "연소득", "월보험료", "가입일",
    "신용카드번호", "신용카드사", "카드 유효기간",
    "혈액형", "아이디", "접속 IP",
]

# ---------------------------------------------------------
# 4. 입력 위젯: 고정 정보 유형 선택 및 데이터 개수 입력
# ---------------------------------------------------------
col1, col2 = st.columns([3, 1])

with col1:
    selected_labels = st.multiselect(
        "생성할 가상 정보 유형을 선택하세요",
        options=ALL_FIELD_LABELS,
        default=["이름", "주민등록번호", "전화번호", "이메일"],
    )

with col2:
    num_rows = st.number_input(
        "생성할 데이터 개수",
        min_value=1,
        value=100,
        step=100,
    )

# ---------------------------------------------------------
# 5. 커스텀 항목: 항목명 + 값 목록을 직접 입력하고, 여러 개 추가 가능
# ---------------------------------------------------------
st.divider()
st.subheader("🧩 커스텀 항목 (선택)")
st.caption(
    "항목 이름과 값 목록(쉼표로 구분)을 입력하면, 생성 시 행마다 목록 중 하나가 "
    "무작위로 들어갑니다. 예) 가입 보험상품 → 실손의료보험, 종신보험, 자동차보험"
)

if "custom_fields" not in st.session_state:
    st.session_state.custom_fields = []


def add_custom_field():
    st.session_state.custom_fields.append(
        {"id": str(uuid.uuid4()), "name": "", "values": ""}
    )


def remove_custom_field(field_id):
    st.session_state.custom_fields = [
        f for f in st.session_state.custom_fields if f["id"] != field_id
    ]


for field in st.session_state.custom_fields:
    c1, c2, c3 = st.columns([2, 4, 1])
    with c1:
        field["name"] = st.text_input(
            "항목 이름", value=field["name"], key=f"name_{field['id']}"
        )
    with c2:
        field["values"] = st.text_input(
            "값 목록 (쉼표로 구분)", value=field["values"], key=f"values_{field['id']}"
        )
    with c3:
        st.write("")
        st.button(
            "삭제",
            key=f"remove_{field['id']}",
            on_click=remove_custom_field,
            args=(field["id"],),
        )

st.button("+ 커스텀 항목 추가", on_click=add_custom_field)

# ---------------------------------------------------------
# 5-2. 코드형 항목 (Primary Key): 자릿수 + 문자 구성을 지정해 코드값 생성
# ---------------------------------------------------------
st.divider()
st.subheader("🔑 코드형 항목 (Primary Key, 선택)")
st.caption(
    "증권번호, 계약번호처럼 자릿수가 동일한 랜덤 코드를 생성합니다. "
    "'유일값'을 켜면 행마다 서로 다른 값이 들어갑니다."
)

CODE_CHARSET_OPTIONS = {
    "숫자만 (0-9)": string.digits,
    "영문 대문자만 (A-Z)": string.ascii_uppercase,
    "영문 대문자 + 숫자": string.ascii_uppercase + string.digits,
    "영문 소문자 + 숫자": string.ascii_lowercase + string.digits,
}

if "code_fields" not in st.session_state:
    st.session_state.code_fields = []


def add_code_field():
    st.session_state.code_fields.append(
        {
            "id": str(uuid.uuid4()),
            "name": "",
            "length": 10,
            "charset_label": "숫자만 (0-9)",
            "unique": True,
        }
    )


def remove_code_field(field_id):
    st.session_state.code_fields = [
        f for f in st.session_state.code_fields if f["id"] != field_id
    ]


for field in st.session_state.code_fields:
    c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 1])
    with c1:
        field["name"] = st.text_input(
            "항목 이름", value=field["name"], key=f"code_name_{field['id']}"
        )
    with c2:
        field["length"] = st.number_input(
            "자릿수",
            min_value=1,
            value=field["length"],
            step=1,
            key=f"code_length_{field['id']}",
        )
    with c3:
        field["charset_label"] = st.selectbox(
            "문자 구성",
            options=list(CODE_CHARSET_OPTIONS.keys()),
            index=list(CODE_CHARSET_OPTIONS.keys()).index(field["charset_label"]),
            key=f"code_charset_{field['id']}",
        )
    with c4:
        field["unique"] = st.checkbox(
            "유일값", value=field["unique"], key=f"code_unique_{field['id']}"
        )
    with c5:
        st.write("")
        st.button(
            "삭제",
            key=f"code_remove_{field['id']}",
            on_click=remove_code_field,
            args=(field["id"],),
        )

st.button("+ 코드형 항목 추가", on_click=add_code_field)

generate_clicked = st.button("가상Data 생성", type="primary")

# ---------------------------------------------------------
# 6. 데이터 생성 및 표시 로직
# ---------------------------------------------------------
if generate_clicked:
    # 이름과 값 목록이 모두 채워진 커스텀 항목만 유효한 것으로 처리
    valid_custom_fields = []
    for field in st.session_state.custom_fields:
        name = field["name"].strip()
        values = [v.strip() for v in field["values"].split(",") if v.strip()]
        if name and values:
            valid_custom_fields.append({"name": name, "values": values})

    # 이름이 채워진 코드형 항목만 유효한 것으로 처리
    valid_code_fields = []
    for field in st.session_state.code_fields:
        name = field["name"].strip()
        if name:
            valid_code_fields.append(
                {
                    "name": name,
                    "length": int(field["length"]),
                    "charset": CODE_CHARSET_OPTIONS[field["charset_label"]],
                    "unique": field["unique"],
                }
            )

    # 입력값 검증
    if not selected_labels and not valid_custom_fields and not valid_code_fields:
        st.warning("⚠️ 하나 이상의 정보 유형(고정/커스텀/코드형)을 선택/입력해 주세요.")
    elif num_rows < 1:
        st.warning("⚠️ 데이터 개수는 1개 이상이어야 합니다.")
    else:
        # 유일값 코드형 항목은 자릿수/문자구성으로 만들 수 있는 조합 수가
        # 요청 건수보다 적으면 생성할 수 없으므로 미리 걸러서 안내
        insufficient = [
            cf
            for cf in valid_code_fields
            if cf["unique"] and (len(cf["charset"]) ** cf["length"]) < num_rows
        ]
        if insufficient:
            names = ", ".join(cf["name"] for cf in insufficient)
            st.error(
                f"⚠️ 다음 코드형 항목은 지정한 자릿수/문자 구성으로 만들 수 있는 "
                f"조합 수가 요청 개수({int(num_rows)}건)보다 적습니다: {names}. "
                "자릿수를 늘리거나 문자 구성 범위를 넓혀주세요."
            )
        else:
            # 코드형 항목별 중복 방지를 위한 집합 (유일값 옵션이 켜진 항목만)
            seen_codes = {cf["name"]: set() for cf in valid_code_fields}

            def generate_code(charset, length, seen):
                for _ in range(1000):
                    code = "".join(random.choices(charset, k=length))
                    if seen is None or code not in seen:
                        if seen is not None:
                            seen.add(code)
                        return code
                raise RuntimeError("코드 생성 재시도 횟수를 초과했습니다.")

            rows = []
            for _ in range(int(num_rows)):
                # 고정 항목 값 미리 계산 (컬럼 순서를 ALL_FIELD_LABELS 기준으로 맞추기 위함)
                pool = {}
                for label, method in SIMPLE_FIELD_MAP.items():
                    if label in selected_labels:
                        pool[label] = getattr(fake, method)()
                for label, calc_fn in CALC_FIELD_MAP.items():
                    if label in selected_labels:
                        pool[label] = calc_fn(fake)

                row = {label: pool[label] for label in ALL_FIELD_LABELS if label in pool}

                # 커스텀 항목(값 목록) 채우기
                for cf in valid_custom_fields:
                    row[cf["name"]] = random.choice(cf["values"])

                # 코드형 항목(Primary Key) 채우기
                for cf in valid_code_fields:
                    seen = seen_codes[cf["name"]] if cf["unique"] else None
                    row[cf["name"]] = generate_code(cf["charset"], cf["length"], seen)

                rows.append(row)

            # DataFrame 변환
            df = pd.DataFrame(rows)

            # 세션 상태에 저장해 두면, 재렌더링 시에도 다운로드 버튼 클릭으로
            # 데이터가 사라지지 않고 유지됩니다.
            st.session_state["fake_df"] = df

# ---------------------------------------------------------
# 7. 생성 결과 표시 및 Excel 다운로드
# ---------------------------------------------------------
if "fake_df" in st.session_state:
    df = st.session_state["fake_df"]

    st.success(f"✅ 총 {len(df)}건의 가상 데이터가 생성되었습니다.")
    st.dataframe(df, use_container_width=True)

    # DataFrame -> Excel(xlsx)을 메모리 버퍼에 기록
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="fake_data")
    excel_buffer.seek(0)

    st.download_button(
        label="📥 Excel 파일로 다운로드 (fake_data.xlsx)",
        data=excel_buffer,
        file_name="fake_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
