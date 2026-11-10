"""Mini NPU Simulator - MAC 연산으로 패턴(Cross / X)을 판정하는 콘솔 프로그램"""

import json
import time

EPSILON = 1e-9        # 동점 판단 허용오차
REPEAT = 10           # 성능 측정 반복 횟수
DATA_FILE = "data.json"

# 여러 표기를 표준 라벨 2개(Cross, X)로 바꾸기 위한 표
LABEL_MAP = {
    "+": "Cross",
    "cross": "Cross",
    "x": "X",
}


# ---------------------------------------------------------
# 1. 핵심 연산
# ---------------------------------------------------------
def mac(pattern, filt):
    """같은 위치끼리 곱해서(Multiply) 모두 더한다(Accumulate)."""
    n = len(pattern)
    total = 0.0
    for i in range(n):
        for j in range(n):
            total += pattern[i][j] * filt[i][j]
    return total


def judge(score_a, score_b, label_a="A", label_b="B"):
    """두 점수를 비교해 판정한다. 차이가 EPSILON보다 작으면 동점."""
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    if score_a > score_b:
        return label_a
    return label_b


def measure_ms(pattern, filt, repeat=REPEAT):
    """mac()을 repeat번 실행해서 1회 평균 시간(ms)을 돌려준다."""
    start = time.perf_counter()
    for _ in range(repeat):
        mac(pattern, filt)
    end = time.perf_counter()
    return (end - start) * 1000 / repeat


# ---------------------------------------------------------
# 2. 보조 함수
# ---------------------------------------------------------
def normalize_label(raw):
    """'+', 'cross', 'x', 'X' 등을 'Cross' 또는 'X'로 바꾼다. 모르면 None."""
    key = str(raw).strip().lower()
    return LABEL_MAP.get(key)


def is_square(matrix, n):
    """matrix가 n×n 크기의 숫자 배열인지 확인한다."""
    if not isinstance(matrix, list) or len(matrix) != n:
        return False
    for row in matrix:
        if not isinstance(row, list) or len(row) != n:
            return False
        for value in row:
            if not isinstance(value, (int, float)):
                return False
    return True


def make_cross(n):
    """n×n 십자가 패턴 생성 (가운데 행과 가운데 열이 1)."""
    mid = n // 2
    return [[1 if (i == mid or j == mid) else 0 for j in range(n)] for i in range(n)]


def make_x(n):
    """n×n X 패턴 생성 (두 대각선이 1)."""
    return [[1 if (i == j or i + j == n - 1) else 0 for j in range(n)] for i in range(n)]


def print_title(text):
    print()
    print("#" + "-" * 40)
    print("# " + text)
    print("#" + "-" * 40)


# ---------------------------------------------------------
# 3. 모드 1: 사용자 입력 (3×3)
# ---------------------------------------------------------
def read_matrix(title, n=3):
    """n줄을 입력받아 n×n 리스트로 돌려준다. 잘못된 줄은 다시 입력받는다."""
    print(f"{title} ({n}줄 입력, 공백 구분)")
    matrix = []
    while len(matrix) < n:
        line = input().strip()
        parts = line.split()
        if len(parts) != n:
            print(f"입력 형식 오류: 각 줄에 {n}개의 숫자를 공백으로 구분해 입력하세요. "
                  f"({len(matrix) + 1}번째 줄 다시 입력)")
            continue
        try:
            row = [float(p) for p in parts]
        except ValueError:
            print(f"입력 형식 오류: 숫자만 입력하세요. ({len(matrix) + 1}번째 줄 다시 입력)")
            continue
        matrix.append(row)
    return matrix


def run_user_mode():
    print_title("[1] 필터 입력")
    filter_a = read_matrix("필터 A")
    print()
    filter_b = read_matrix("필터 B")
    print("✓ 필터 A, B 저장 완료")

    print_title("[2] 패턴 입력")
    pattern = read_matrix("패턴")

    print_title("[3] MAC 결과")
    score_a = mac(pattern, filter_a)
    score_b = mac(pattern, filter_b)
    elapsed = measure_ms(pattern, filter_a)
    result = judge(score_a, score_b, "A", "B")

    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"연산 시간(평균/{REPEAT}회): {elapsed:.4f} ms")
    if result == "UNDECIDED":
        print(f"판정: 판정 불가 (|A-B| < {EPSILON})")
    else:
        print(f"판정: {result}")

    print_title(f"[4] 성능 분석 (평균/{REPEAT}회)")
    print_performance([3])


# ---------------------------------------------------------
# 4. 모드 2: data.json 분석
# ---------------------------------------------------------
def load_filters(data):
    """filters 부분을 읽어 {5: {'Cross': [...], 'X': [...]}, ...} 형태로 만든다."""
    filters = {}
    raw_filters = data.get("filters", {})
    for size_key, pair in raw_filters.items():
        try:
            n = int(size_key.split("_")[1])          # 'size_5' -> 5
        except (IndexError, ValueError):
            print(f"✗ {size_key}: 키 형식 오류 (size_N 형태가 아님)")
            continue
        if not isinstance(pair, dict):
            print(f"✗ {size_key}: 필터 형식 오류")
            continue

        normalized = {}
        for label_key, matrix in pair.items():
            label = normalize_label(label_key)       # 'cross' -> 'Cross'
            if label is None:
                print(f"✗ {size_key}: 알 수 없는 필터 이름 '{label_key}'")
                continue
            if not is_square(matrix, n):
                print(f"✗ {size_key}: {label} 필터 크기가 {n}×{n}이 아님")
                continue
            normalized[label] = matrix

        if "Cross" in normalized and "X" in normalized:
            filters[n] = normalized
            print(f"✓ {size_key:<8} 필터 로드 완료 (Cross, X)")
        else:
            print(f"✗ {size_key}: Cross/X 필터가 모두 있어야 합니다")
    return filters


def analyze_patterns(data, filters):
    """패턴마다 MAC 점수 계산·판정·PASS/FAIL 비교. 결과 목록을 돌려준다."""
    results = []   # (케이스 이름, 통과 여부, 실패 사유)
    raw_patterns = data.get("patterns", {})

    for case_id, case in raw_patterns.items():
        print(f"--- {case_id} ---")

        # (1) 키에서 N 추출: 'size_13_2' -> 13
        try:
            n = int(case_id.split("_")[1])
        except (IndexError, ValueError):
            reason = "키 형식 오류 (size_N_idx 형태가 아님)"
            print(f"FAIL ({reason})")
            results.append((case_id, False, reason))
            continue

        # (2) 해당 크기 필터가 있는지
        if n not in filters:
            reason = f"size_{n} 필터 없음"
            print(f"FAIL ({reason})")
            results.append((case_id, False, reason))
            continue

        # (3) 패턴 형식/크기 검증
        if not isinstance(case, dict):
            reason = "패턴 항목 형식 오류"
            print(f"FAIL ({reason})")
            results.append((case_id, False, reason))
            continue
        pattern = case.get("input")
        if not is_square(pattern, n):
            reason = f"패턴 크기가 필터 크기({n}×{n})와 다름"
            print(f"FAIL ({reason})")
            results.append((case_id, False, reason))
            continue

        # (4) expected 라벨 정규화
        expected = normalize_label(case.get("expected", ""))
        if expected is None:
            reason = f"expected 라벨을 알 수 없음: {case.get('expected')!r}"
            print(f"FAIL ({reason})")
            results.append((case_id, False, reason))
            continue

        # (5) MAC 연산 + 판정
        cross_score = mac(pattern, filters[n]["Cross"])
        x_score = mac(pattern, filters[n]["X"])
        decision = judge(cross_score, x_score, "Cross", "X")

        print(f"Cross 점수: {cross_score}")
        print(f"X 점수: {x_score}")
        if decision == expected:
            print(f"판정: {decision} | expected: {expected} | PASS")
            results.append((case_id, True, ""))
        else:
            if decision == "UNDECIDED":
                reason = "동점(UNDECIDED) 처리 규칙에 따라 FAIL"
            else:
                reason = f"판정 {decision} ≠ expected {expected}"
            print(f"판정: {decision} | expected: {expected} | FAIL")
            results.append((case_id, False, reason))
    return results


def print_performance(sizes):
    """크기별로 생성한 Cross 패턴·필터로 평균 MAC 시간을 표로 출력한다."""
    print(f"{'크기':<8}{'평균 시간(ms)':>16}{'연산 횟수':>12}")
    print("-" * 40)
    for n in sizes:
        pattern = make_cross(n)
        filt = make_cross(n)
        elapsed = measure_ms(pattern, filt)
        print(f"{f'{n}×{n}':<8}{elapsed:>16.4f}{n * n:>12}")


def print_summary(results):
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed
    print(f"총 테스트: {total}개")
    print(f"통과: {passed}개")
    print(f"실패: {failed}개")
    if failed:
        print()
        print("실패 케이스:")
        for case_id, ok, reason in results:
            if not ok:
                print(f"- {case_id}: {reason}")


def run_json_mode():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"{DATA_FILE} 파일을 찾을 수 없습니다. main.py와 같은 폴더에 두세요.")
        return
    except json.JSONDecodeError as e:
        print(f"{DATA_FILE} 형식 오류: {e}")
        return

    print_title("[1] 필터 로드")
    filters = load_filters(data)

    print_title("[2] 패턴 분석 (라벨 정규화 적용)")
    results = analyze_patterns(data, filters)

    print_title(f"[3] 성능 분석 (평균/{REPEAT}회)")
    print_performance([3, 5, 13, 25])

    print_title("[4] 결과 요약")
    print_summary(results)


# ---------------------------------------------------------
# 5. 프로그램 시작
# ---------------------------------------------------------
def main():
    print("=== Mini NPU Simulator ===")
    print()
    print("[모드 선택]")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")
    while True:
        choice = input("선택: ").strip()
        if choice == "1":
            run_user_mode()
            break
        if choice == "2":
            run_json_mode()
            break
        print("1 또는 2를 입력하세요.")


if __name__ == "__main__":
    main()