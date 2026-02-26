from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, List, Any, Tuple
import math


# ----------------------------
# Utilities
# ----------------------------
def fmt(x: Optional[float], digits: int = 1) -> str:
    if x is None:
        return "-"
    if math.isfinite(x):
        s = f"{x:.{digits}f}"
        if digits > 0 and s.endswith("." + "0" * digits):
            s = s[: -(digits + 1)]
        return s
    return "-"


# ----------------------------
# Data models
# ----------------------------
@dataclass
class Person:
    age: int
    sex: str  # 'male' or 'female'


@dataclass
class LabInput:
    value: Optional[float] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    unit: str = ""


@dataclass
class ItemResult:
    key: str
    name_ko: str
    value: Optional[float]
    unit: str
    status: str  # low/normal/high/borderline/critical/unknown
    short: str
    easy_explain: str
    possible_causes: List[str]
    next_steps: List[str]
    warnings: List[str]
    evidence: List[str]


# ----------------------------
# UI helpers / constants
# ----------------------------
LAB_KEYS = [
    "fasting_glucose", "hba1c", "total_chol", "ldl", "hdl", "tg",
    "ast", "alt", "ggt", "creatinine", "egfr", "uric_acid", "sbp", "dbp"
]

DISPLAY_NAMES_KO = {
    "fasting_glucose": "공복혈당",
    "hba1c": "당화혈색소(HbA1c)",
    "total_chol": "총콜레스테롤",
    "ldl": "LDL 콜레스테롤",
    "hdl": "HDL 콜레스테롤",
    "tg": "중성지방(TG)",
    "ast": "AST(GOT)",
    "alt": "ALT(GPT)",
    "ggt": "감마지티피(GGT)",
    "creatinine": "크레아티닌",
    "egfr": "eGFR(추정사구체여과율)",
    "uric_acid": "요산",
    "sbp": "수축기혈압(SBP)",
    "dbp": "이완기혈압(DBP)",
    "bp": "혈압",
}

UNITS_DEFAULT = {
    "fasting_glucose": "mg/dL",
    "hba1c": "%",
    "total_chol": "mg/dL",
    "ldl": "mg/dL",
    "hdl": "mg/dL",
    "tg": "mg/dL",
    "ast": "U/L",
    "alt": "U/L",
    "ggt": "U/L",
    "creatinine": "mg/dL",
    "egfr": "mL/min/1.73m²",
    "uric_acid": "mg/dL",
    "sbp": "mmHg",
    "dbp": "mmHg",
}


# ----------------------------
# Simple reference ranges (generic defaults)
# NOTE: labs vary by institution. Prefer user-provided ref ranges.
# ----------------------------
@dataclass(frozen=True)
class RefRange:
    low: Optional[float] = None
    high: Optional[float] = None
    unit: str = ""

    def classify(self, value: float) -> str:
        if self.low is not None and value < self.low:
            return "low"
        if self.high is not None and value > self.high:
            return "high"
        if self.low is None and self.high is None:
            return "unknown"
        return "normal"


DEFAULT_RANGES: Dict[str, RefRange] = {
    "fasting_glucose": RefRange(70, 99, "mg/dL"),
    "hba1c": RefRange(4.0, 5.6, "%"),
    "total_chol": RefRange(None, 199, "mg/dL"),
    "ldl": RefRange(None, 129, "mg/dL"),
    "hdl_male": RefRange(40, None, "mg/dL"),
    "hdl_female": RefRange(50, None, "mg/dL"),
    "tg": RefRange(None, 149, "mg/dL"),
    "ast": RefRange(None, 40, "U/L"),
    "alt": RefRange(None, 40, "U/L"),
    "ggt_male": RefRange(None, 60, "U/L"),
    "ggt_female": RefRange(None, 40, "U/L"),
    "creatinine_male": RefRange(0.74, 1.35, "mg/dL"),
    "creatinine_female": RefRange(0.59, 1.04, "mg/dL"),
    "egfr": RefRange(90, None, "mL/min/1.73m²"),
    "uric_male": RefRange(3.4, 7.0, "mg/dL"),
    "uric_female": RefRange(2.4, 6.0, "mg/dL"),
}


def get_default_ref(key: str, p: Person) -> RefRange:
    if key == "hdl":
        return DEFAULT_RANGES["hdl_male"] if p.sex == "male" else DEFAULT_RANGES["hdl_female"]
    if key == "ggt":
        return DEFAULT_RANGES["ggt_male"] if p.sex == "male" else DEFAULT_RANGES["ggt_female"]
    if key == "creatinine":
        return DEFAULT_RANGES["creatinine_male"] if p.sex == "male" else DEFAULT_RANGES["creatinine_female"]
    if key == "uric_acid":
        return DEFAULT_RANGES["uric_male"] if p.sex == "male" else DEFAULT_RANGES["uric_female"]
    return DEFAULT_RANGES.get(key, RefRange(unit=UNITS_DEFAULT.get(key, "")))


def classify_with_ref(value: float, li: LabInput, rr: RefRange) -> Tuple[str, RefRange]:
    low = li.ref_low if li.ref_low is not None else rr.low
    high = li.ref_high if li.ref_high is not None else rr.high
    rr2 = RefRange(low, high, rr.unit)
    return rr2.classify(value), rr2


def bp_status(sbp: float, dbp: float) -> Tuple[str, str]:
    if sbp >= 180 or dbp >= 120:
        return "critical", "혈압이 매우 높아 즉시 의료진 평가가 필요할 수 있습니다."
    if sbp >= 140 or dbp >= 90:
        return "high", "혈압이 높은 범주(일반 기준에서 2단계)에 해당할 수 있습니다."
    if (130 <= sbp <= 139) or (80 <= dbp <= 89):
        return "borderline", "혈압이 높은 범주(일반 기준에서 1단계)에 해당할 수 있습니다."
    if (120 <= sbp <= 129) and dbp < 80:
        return "borderline", "혈압이 정상보다 약간 높은 범주(상승)에 해당할 수 있습니다."
    return "normal", "혈압이 일반적인 정상 범주에 해당합니다."


# ----------------------------
# Interpretation
# ----------------------------
def interpret(person: Person, labs: Dict[str, LabInput]) -> List[ItemResult]:
    results: List[ItemResult] = []

    def add(
        key: str,
        status: str,
        short: str,
        explain: str,
        causes: List[str],
        steps: List[str],
        warnings: List[str],
        evidence: List[str],
        value: Optional[float],
        unit: str,
    ):
        results.append(ItemResult(
            key=key,
            name_ko=DISPLAY_NAMES_KO.get(key, key),
            value=value,
            unit=unit,
            status=status,
            short=short,
            easy_explain=explain,
            possible_causes=causes,
            next_steps=steps,
            warnings=warnings,
            evidence=evidence,
        ))

    # labs
    for key in ["fasting_glucose","hba1c","total_chol","ldl","hdl","tg","ast","alt","ggt","creatinine","egfr","uric_acid"]:
        li = labs.get(key, LabInput())
        unit = li.unit or UNITS_DEFAULT.get(key, "")

        if li.value is None:
            add(key, "unknown", "입력값이 없습니다.", "수치가 있어야 해석할 수 있어요.",
                [], ["검진표의 해당 수치를 입력하세요."], [], [], None, unit)
            continue

        rr = get_default_ref(key, person)
        cls, rr2 = classify_with_ref(li.value, li, rr)
        ev = []
        if rr2.low is not None or rr2.high is not None:
            ev.append(f"참고치(기본/입력 기반): {fmt(rr2.low)} ~ {fmt(rr2.high)} {unit}".strip())

        name = DISPLAY_NAMES_KO.get(key, key)

        # Custom rules (MVP)
        if key == "fasting_glucose":
            v = li.value
            status = cls
            short = f"{name}이(가) 참고치 기준으로 '{'정상' if cls=='normal' else '높음' if cls=='high' else '낮음' if cls=='low' else '판단불가'}' 범주입니다."
            explain = "공복혈당은 공복 상태의 혈당을 보는 지표예요. 단 한 번의 수치만으로 질병을 확정하진 않습니다."
            causes, steps, warnings = [], ["최근 식사/운동/수면/스트레스가 영향을 줄 수 있어요."], ["진단을 확정하지 않습니다. 의료진 상담이 필요합니다."]
            if v >= 126:
                status = "high"
                short = f"{name}이 126 이상으로 높게 측정되었습니다(단회 측정만으로 확진하지 않음)."
                causes = ["당 대사 이상 가능성", "컨디션/약물/스트레스 영향"]
                steps += ["재검 또는 HbA1c 등 추가 확인을 의료진과 상의하세요."]
            elif 100 <= v <= 125:
                status = "borderline"
                short = f"{name}이 100~125 범주로 경계(상승)일 수 있습니다."
                causes = ["체중 증가/운동 부족", "탄수화물 섭취 패턴", "수면 부족"]
                steps += ["식습관 조정, 운동(유산소+근력), 1~3개월 후 재검을 고려하세요."]
            elif v < 70:
                status = "low"
                short = f"{name}이 낮게 측정되었습니다."
                causes = ["공복 시간 과도", "일부 약물 영향", "컨디션 영향"]
                steps += ["저혈당 증상이 있으면 의료진과 상담하세요."]
            add(key, status, short, explain, causes, steps, warnings, ev, v, unit)
            continue

        if key == "hba1c":
            v = li.value
            status = cls
            short = f"{name}이(가) 참고치 기준으로 '{'정상' if cls=='normal' else '높음' if cls=='high' else '낮음' if cls=='low' else '판단불가'}' 범주입니다."
            explain = "HbA1c는 최근 2~3개월 평균 혈당 상태를 간접적으로 보여주는 지표예요."
            causes, steps, warnings = [], ["추세를 보는 데 유리합니다."], ["진단을 확정하지 않습니다. 의료진과 상의하세요."]
            if v >= 6.5:
                status = "high"
                short = f"{name}이 6.5 이상으로 높게 측정되었습니다(확진은 의료진 판단)."
                causes = ["혈당 조절 문제 가능성"]
                steps += ["공복혈당/추가검사를 의료진과 상의하세요."]
            elif 5.7 <= v <= 6.4:
                status = "borderline"
                short = f"{name}이 5.7~6.4 범주로 경계(상승)일 수 있습니다."
                causes = ["체중/활동량/식습관 영향"]
                steps += ["식사/운동/체중 관리 후 3개월 내 재검을 고려하세요."]
            add(key, status, short, explain, causes, steps, warnings, ev, v, unit)
            continue

        if key in ["ast","alt","ggt"]:
            v = li.value
            status = cls
            explain = f"{name}는 간/담도계 또는 일부 근육 손상 등과 연관될 수 있는 효소 지표예요. 패턴과 추적이 중요합니다."
            causes = []
            steps = ["최근 음주, 격한 운동, 약물/보충제 복용 여부를 함께 확인하세요."]
            warnings = ["지속 상승하거나 증상이 동반되면 의료진 상담이 필요합니다."]
            ul = rr2.high
            if ul is not None:
                if v >= 5 * ul:
                    status = "high"
                    short = f"{name}이 참고치 상한의 5배 이상으로 크게 상승했습니다."
                    causes = ["급성 간손상 가능성(여러 원인 가능)", "약물/바이러스/알코올 등"]
                    steps += ["빠르게 의료진 상담/재검을 권합니다."]
                elif v >= 2 * ul:
                    status = "high"
                    short = f"{name}이 참고치 상한의 2배 이상으로 상승했습니다."
                    causes = ["지방간/음주/약물/바이러스 등"]
                    steps += ["의료진과 원인 평가를 고려하세요."]
                elif v > ul:
                    status = "borderline"
                    short = f"{name}이 참고치 상한을 약간 초과했습니다."
                    causes = ["일시적 상승(음주/운동/약물)", "지방간 등"]
                    steps += ["2~8주 후 재검을 고려하세요."]
                else:
                    short = f"{name}이 참고치 범위에 있습니다."
            else:
                short = f"{name}이(가) 참고치 기준으로 '{'정상' if cls=='normal' else '높음' if cls=='high' else '낮음' if cls=='low' else '판단불가'}' 범주입니다."
            add(key, status, short, explain, causes, steps, warnings, ev, v, unit)
            continue

        if key == "egfr":
            v = li.value
            explain = "eGFR은 신장이 혈액을 걸러내는 능력을 추정한 값이에요. 낮을수록 신장 기능 저하 가능성을 시사할 수 있습니다."
            causes = []
            steps = ["크레아티닌, 소변검사, 혈압/혈당 등과 함께 종합 해석합니다."]
            warnings = ["연령/근육량 등에 따라 해석이 달라질 수 있습니다."]
            if v < 30:
                status = "high"
                short = f"{name}이 30 미만으로 낮습니다. 빠른 의료진 평가가 필요할 수 있습니다."
                causes = ["신장 기능 저하 가능성"]
                steps += ["가급적 빨리 의료진 상담을 권합니다."]
            elif 30 <= v < 60:
                status = "high"
                short = f"{name}이 30~59 범주로 낮습니다. 추가 평가가 필요할 수 있습니다."
                causes = ["신장 기능 저하 가능성", "만성질환 영향"]
                steps += ["의료진과 상담하여 추적 계획을 세우세요."]
            elif 60 <= v < 90:
                status = "borderline"
                short = f"{name}이 60~89 범주로 다소 낮을 수 있습니다."
                causes = ["연령/체격/수분 상태 영향", "초기 변화 가능성"]
                steps += ["생활습관 점검 후 추적을 고려하세요."]
            else:
                status = "normal"
                short = f"{name}이 90 이상으로 일반적인 정상 범주입니다."
            add(key, status, short, explain, causes, steps, warnings, ev, v, unit)
            continue

        # Default simple classification
        status = cls
        short = f"{name}이(가) 참고치 기준으로 '{'정상' if cls=='normal' else '높음' if cls=='high' else '낮음' if cls=='low' else '판단불가'}' 범주입니다."
        explain = "이 항목은 입력된 수치와 참고치 기준으로 분류했습니다."
        causes = []
        steps = ["해당 항목은 개인 병력/증상과 함께 종합 해석하는 것이 좋아요."]
        warnings = ["진단을 확정하지 않습니다. 필요 시 의료진 상담을 권합니다."]
        add(key, status, short, explain, causes, steps, warnings, ev, li.value, unit)

    # Blood pressure
    sbp = labs.get("sbp", LabInput()).value
    dbp = labs.get("dbp", LabInput()).value
    if sbp is None or dbp is None:
        add("bp", "unknown", "혈압 입력값이 부족합니다.", "SBP/DBP가 모두 있어야 해석할 수 있어요.",
            [], ["SBP/DBP를 입력하세요(예: 120/80)."], [], ["일반적 혈압 범주(진단 아님)"], None, "mmHg")
    else:
        status, short = bp_status(sbp, dbp)
        explain = "혈압은 측정 환경(긴장, 카페인, 운동 직후) 영향을 크게 받아요. 반복 측정 평균이 중요합니다."
        causes = ["스트레스/수면 부족", "체중 증가", "염분 섭취", "카페인/음주"]
        steps = ["집에서 아침/저녁 1~2주 측정해 평균을 보세요.", "염분 줄이기, 체중/운동 관리가 도움이 됩니다."]
        warnings = ["가슴통증/호흡곤란/신경학적 증상 동반 시 즉시 진료가 필요할 수 있습니다."]
        add("bp", status, short, explain, causes, steps, warnings, ["일반적 혈압 범주(진단 아님)"], None, "mmHg")

    return results


def make_report(person: Person, results: List[ItemResult]) -> Dict[str, Any]:
    critical = [r for r in results if r.status == "critical"]
    high = [r for r in results if r.status == "high"]
    borderline = [r for r in results if r.status in ("borderline", "low")]

    summary: List[str] = []
    if critical:
        summary.append("⚠️ **즉시 확인이 필요한 신호가 있을 수 있습니다.**")
        for r in critical:
            summary.append(f"- {r.name_ko} ({r.status})")
    if high:
        summary.append("🔶 **높은 범주로 분류된 항목**")
        for r in high:
            summary.append(f"- {r.name_ko}: {fmt(r.value)} {r.unit}")
    if borderline:
        summary.append("🟡 **경계/낮음 범주 항목**")
        for r in borderline:
            summary.append(f"- {r.name_ko}: {fmt(r.value)} {r.unit} ({r.status})")

    if not (critical or high or borderline):
        summary.append("✅ **입력된 항목 기준으로 크게 벗어난 신호가 없어 보입니다.** (단, 참고치/개인 상황에 따라 달라질 수 있음)")

    disclaimer = [
        "이 결과는 **의료행위(진단/처방)**가 아니라, 입력된 수치/참고치 기반 **정보 제공용 설명**입니다.",
        "증상이 있거나 수치가 걱정되면 **의료진과 상담**하세요.",
        "검사기관/개인 상태에 따라 참고치와 해석이 달라질 수 있습니다.",
    ]

    return {"person": {"age": person.age, "sex": person.sex}, "summary": summary, "disclaimer": disclaimer}