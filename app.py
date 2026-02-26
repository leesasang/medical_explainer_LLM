import streamlit as st
from hc_core import Person, LabInput, interpret, make_report, LAB_KEYS, DISPLAY_NAMES_KO, UNITS_DEFAULT

st.set_page_config(page_title="건강검진 수치 쉬운 설명기 (MVP)", layout="wide")

st.title("🩺 건강검진 수치 쉬운 설명기 (MVP)")
st.caption("입력된 수치와 참고치를 기반으로 **쉬운 설명 + 다음 행동**을 제공합니다. (진단/처방 아님)")

with st.sidebar:
    st.header("기본 정보")
    age = st.number_input("나이", min_value=1, max_value=120, value=25, step=1)
    sex = st.selectbox("성별", options=[("male", "남성"), ("female", "여성")], format_func=lambda x: x[1])[0]

    st.divider()
    st.subheader("참고치 입력 방식")
    use_custom_ref = st.toggle("검진표 참고치를 직접 입력할래요", value=True)
    st.caption("추천: 검진기관 참고치가 가장 안전/정확합니다.")

person = Person(age=int(age), sex=sex)

st.subheader("1) 검사 수치 입력")
st.write("필요한 항목만 입력해도 됩니다. (비워두면 해당 항목은 '입력값 없음')")

labs = {}

# Split UI into columns
col1, col2 = st.columns(2, gap="large")

def lab_row(container, key: str):
    name = DISPLAY_NAMES_KO.get(key, key)
    unit = UNITS_DEFAULT.get(key, "")
    with container:
        st.markdown(f"### {name}")
        v = st.text_input(f"{name} 수치", value="", key=f"v_{key}", placeholder="예: 95")
        val = float(v) if v.strip() != "" else None

        ref_low = ref_high = None
        if use_custom_ref:
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                lo = st.text_input("참고치 하한", value="", key=f"lo_{key}", placeholder="예: 70")
            with c2:
                hi = st.text_input("참고치 상한", value="", key=f"hi_{key}", placeholder="예: 99")
            with c3:
                u = st.text_input("단위", value=unit, key=f"u_{key}")
            ref_low = float(lo) if lo.strip() != "" else None
            ref_high = float(hi) if hi.strip() != "" else None
            unit_final = u.strip() if u.strip() else unit
        else:
            unit_final = unit

        labs[key] = LabInput(value=val, ref_low=ref_low, ref_high=ref_high, unit=unit_final)

# Group fields
left_keys = ["fasting_glucose", "hba1c", "total_chol", "ldl", "hdl", "tg", "sbp", "dbp"]
right_keys = ["ast", "alt", "ggt", "creatinine", "egfr", "uric_acid"]

for k in left_keys:
    lab_row(col1, k)

for k in right_keys:
    lab_row(col2, k)

st.divider()

run = st.button("2) 해석 생성", type="primary", use_container_width=True)

if run:
    results = interpret(person, labs)
    report = make_report(person, results)

    st.subheader("2) 요약")
    for line in report["summary"]:
        st.markdown(line)

    st.divider()
    st.subheader("3) 항목별 상세 설명")

    # Status to emoji
    emoji = {
        "critical": "🛑",
        "high": "🔶",
        "borderline": "🟡",
        "low": "🔵",
        "normal": "✅",
        "unknown": "❔",
    }

    for r in results:
        with st.expander(f"{emoji.get(r.status,'❔')} {r.name_ko}"):
            if r.value is not None:
                st.markdown(f"**입력 수치:** {r.value} {r.unit}")
            else:
                st.markdown("**입력 수치:** (없음)")

            st.markdown(f"**판정:** `{r.status}`")
            st.markdown(f"**한 줄 요약:** {r.short}")
            st.markdown(f"**쉬운 설명:** {r.easy_explain}")

            if r.possible_causes:
                st.markdown("**가능한 요인(일반):**")
                st.write("\n".join([f"- {c}" for c in r.possible_causes]))

            if r.next_steps:
                st.markdown("**다음 행동(일반):**")
                st.write("\n".join([f"- {s}" for s in r.next_steps]))

            if r.warnings:
                st.markdown("**주의:**")
                st.write("\n".join([f"- {w}" for w in r.warnings]))

            if r.evidence:
                st.markdown("**근거/기준:**")
                st.write("\n".join([f"- {e}" for e in r.evidence]))

    st.divider()
    st.subheader("면책/주의")
    for d in report["disclaimer"]:
        st.markdown(f"- {d}")