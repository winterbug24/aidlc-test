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
