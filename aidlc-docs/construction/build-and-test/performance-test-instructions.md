# 성능 테스트 지침

## 목적
이 프로젝트는 로컬 단일 사용자용이라 부하 테스트와 스트레스 테스트는 대상이 아니다 (NFR 요구사항 PERF-01, SCAL-01).
여기서는 설계 목표 하나만 확인한다.

## 성능 요구사항

| 항목 | 목표 | 근거 |
|---|---|---|
| 목록 조회 응답 시간 | 활성 항목 1,000건에서 200ms 이내 | PERF-01 |
| 처리량, 동시 사용자 | 정의하지 않음 (동시 사용자 1명 가정) | SCAL-01 |
| 인덱스 사용 | 목록 조회와 중복 판정이 항목 수에 따라 급격히 느려지지 않음 | PERF-02 |

요청 제한(분당 60회)이 있으므로 그 이상의 처리량은 의미가 없다.

## 측정 방법

아래 스크립트를 임의의 파일(예: `/tmp/perf_check.py`)로 저장해 실행한다. 임시 DB에 1,000건을 넣고 응답 시간을 잰다. 요청 제한은 끈 상태(테스트 설정)다.

```python
import statistics, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, "tests")
from conftest import AUTH, make_config
from todo_api.app import create_app

with tempfile.TemporaryDirectory() as tmp:
    client = create_app(make_config(Path(tmp))).test_client()
    for i in range(1000):
        assert client.post("/todos", json={"title": f"할 일 {i}"}, headers=AUTH).status_code == 201

    def measure(path, n=100):
        samples = []
        for _ in range(n):
            started = time.perf_counter()
            assert client.get(path, headers=AUTH).status_code == 200
            samples.append((time.perf_counter() - started) * 1000)
        samples.sort()
        return statistics.median(samples), samples[int(n * 0.95) - 1], max(samples)

    print("list 1000   median/p95/max ms: %.2f / %.2f / %.2f" % measure("/todos"))
    print("list filter median/p95/max ms: %.2f / %.2f / %.2f" % measure("/todos?completed=false"))
    print("get one     median/p95/max ms: %.2f / %.2f / %.2f" % measure("/todos/500"))
```

```bash
PYTHONPATH=src .venv/bin/python /tmp/perf_check.py
```

## 측정 결과 (2026-10-12, WSL Ubuntu, Python 3.12.3)

| 동작 | 중앙값 | p95 | 최대 | 목표 | 판정 |
|---|---|---|---|---|---|
| 목록 조회 (1,000건) | 2.66ms | 3.46ms | 16.36ms | 200ms 이내 | 충족 |
| 목록 조회 + 완료 필터 | 2.64ms | 3.42ms | 19.70ms | 200ms 이내 | 충족 |
| 단건 조회 | 0.52ms | 0.71ms | 0.96ms | - | - |
| 1,000건 중 중복 판정 (409) | 0.67ms (1회 측정) | - | - | - | - |
| 추가 1,000회 | 평균 4.53ms | - | - | - | - |

측정은 Flask 테스트 클라이언트 기준이다. 실제 HTTP 연결과 Waitress 처리 시간은 포함하지 않는다. 로컬 루프백에서는 이 차이가 보통 수 ms 수준이지만 따로 측정하지는 않았다.

## 목표를 넘으면
1. 로그의 `request` 이벤트에서 `duration_ms`가 큰 요청을 찾는다
2. DB 파일이 느린 저장소(네트워크 드라이브 등)에 있는지 확인한다
3. 항목 수가 수만 건을 넘으면 페이지네이션 추가를 검토한다 (현재 범위 밖)

## 2차 워크플로(웹 화면)의 성능 확인

### 기준

| 항목 | 목표 | 근거 |
|---|---|---|
| 화면을 처음 여는 데 드는 요청 | 4회 (아이콘 요청 없음) | WPERF-01 |
| 사용자 동작 하나당 API 호출 | 1회 이내 | WPERF-02 |
| 화면 파일 크기 합계 | 60KB 이내 | WPERF-03 |
| 1,000건 목록에서의 조작 | 정상 동작 | WPERF-04 |
| 가만히 둔 화면의 요청 | 0회 | WPERF-05 |

### 자동 확인
위 다섯 항목은 테스트로 고정되어 있다.
```bash
.venv/bin/python -m pytest tests/test_ui_display.py tests/test_web_routes.py -k "requests or action or thousand or small" -q
```

### 측정 결과 (2026-10-12, WSL Ubuntu, Playwright Chromium 화면 없는 모드)

| 동작 | 결과 | 비고 |
|---|---|---|
| 화면 파일 크기 | 27.3KB (HTML 4.9, CSS 5.4, JavaScript 17.1) | 기준 60KB |
| 1,000건이 있는 화면 열기 | 중앙값 80ms, 최대 84ms (5회) | 새로 고침부터 마지막 항목이 그려질 때까지 |
| 1,000건 위에 추가 | 66ms | 입력부터 항목이 나타날 때까지 |
| 완료 체크 | 79ms | 클릭부터 저장 완료 표시까지 |
| 필터 변경 (1,000건 다시 그리기) | 98ms | 클릭부터 목록이 다시 그려질 때까지 |

측정은 서버와 브라우저가 모두 WSL 안에 있는 조건이다. 실제 사용에서는 브라우저가 Windows에 있어 WSL과의 루프백 전달 시간이 더해지는데, 그 조건은 측정하지 않았다. 각 동작은 한 번씩만 잰 값이라(화면 열기 제외) 편차를 알 수 없다.
