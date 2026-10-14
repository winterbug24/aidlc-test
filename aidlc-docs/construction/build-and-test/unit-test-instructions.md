# 단위 테스트 실행 지침

테스트는 pytest로 실행한다. 예제 기반 테스트, 속성 기반 테스트(Hypothesis), 화면 테스트(Playwright)가 같은 명령으로 함께 실행된다.
테스트마다 임시 DB를 쓰므로 실제 DB(`instance/todo.db`)에는 영향이 없고 환경 변수도 필요 없다.

## 실행

### 1. 전체 테스트
```bash
.venv/bin/python -m pytest
```

### 2. 범위를 좁혀 실행
```bash
# 업무 로직과 저장소 계층 단위 테스트
.venv/bin/python -m pytest tests/test_validation.py tests/test_serialization.py tests/test_config.py tests/test_repository.py

# 속성 기반 테스트만
.venv/bin/python -m pytest tests/test_properties.py

# 이름으로 하나만
.venv/bin/python -m pytest -k "duplicate"
```

### 3. 속성 기반 테스트 재현 (PBT-08)
```bash
# 같은 시드로 다시 실행
.venv/bin/python -m pytest --hypothesis-seed=20261012

# 통계 보기 (예제 수, 축소 단계)
.venv/bin/python -m pytest tests/test_properties.py --hypothesis-show-statistics
```

- 속성 기반 테스트가 실패하면 Hypothesis가 입력을 가장 작은 반례로 줄여 출력하고, 재현용 `@reproduce_failure` 코드도 함께 출력한다.
- 축소(shrinking)는 끄지 않았다.
- CI는 실행마다 시드를 로그에 남긴다 (`Hypothesis seed: <값>`). 그 값을 `--hypothesis-seed`에 넣으면 같은 실행을 재현한다.
- 실패한 반례는 예제 기반 테스트로 추가해 회귀를 막는다.

## 테스트 구성

| 파일 | 테스트 수 | 종류 | 대상 |
|---|---|---|---|
| `test_validation.py` | 28 | 예제 기반 | 제목 정규화, 스키마 검증 |
| `test_serialization.py` | 4 | 예제 기반 | 행과 Todo 표현 변환 |
| `test_config.py` | 11 | 예제 기반 | 환경 변수, API 키 검증, 시작 거부 (RT-08) |
| `test_repository.py` | 12 | 예제 기반 | SQL, 인덱스, 제약, 트랜잭션 롤백 |
| `test_todos_api.py` | 49 | 예제 기반 | 엔드포인트 5개의 정상/오류 케이스 |
| `test_auth.py` | 17 | 예제 기반 | 기본 거부, 정보 비노출 |
| `test_rate_limit.py` | 6 | 예제 기반 | 전체 한도, 인증 실패 한도 |
| `test_errors.py` | 10 | 예제 기반 | 오류 형식, 응답 헤더, 로그 |
| `test_health.py` | 3 | 예제 기반 | 상태 확인 |
| `test_properties.py` | 9 | 속성 기반 | P-01~P-09 (상태 기반 모델 포함) |
| `test_resilience.py` | 5 | 복원력 | RT-01~04 |
| `test_backup.py` | 7 | 복원력 | RT-05~07, 파일 권한, 명령줄 |
| **1차 워크플로 합계** | **161** | | |

## 결과 확인
- **기대 결과**: `343 passed`, 실패 0. 실행 시간 약 65초 (화면 테스트를 빼면 `274 passed`)
- **커버리지**: 측정하지 않는다. 커버리지 도구를 의존성에 포함하지 않았다. 필요하면 `pytest-cov`를 `requirements-dev.txt`에 고정해 추가한다
- **보고서 위치**: 터미널 출력. 파일이 필요하면 `--junitxml=report.xml`을 붙인다

## 실패 시
1. 출력 맨 아래 `short test summary`에서 실패한 테스트 이름을 확인한다
2. `-x -vv` 옵션으로 첫 실패에서 멈추고 자세히 본다
3. 속성 기반 테스트라면 출력된 최소 반례와 시드로 재현한다
4. 코드를 고친 뒤 전체 테스트를 다시 실행한다

## 2차 워크플로(웹 화면)에서 추가된 테스트

### 실행
```bash
# 화면 테스트를 빼고 빠르게 (브라우저 불필요)
.venv/bin/python -m pytest -m "not e2e"

# 실행 로직과 서버 쪽 화면 테스트만
.venv/bin/python -m pytest tests/test_launcher.py tests/test_launcher_properties.py tests/test_security_headers.py tests/test_web_routes.py
```

### 추가된 구성

| 파일 | 테스트 수 | 종류 | 대상 |
|---|---|---|---|
| `test_security_headers.py` | 13 | 예제 기반 | 모든 종류의 응답에 붙는 보안 헤더, 정책 내용 |
| `test_web_routes.py` | 27 | 예제 기반 | 화면 파일 제공, 경로 탈출 차단, 공개 범위, 인라인 코드 없음 |
| `test_launcher.py` | 31 (3차에서 55로 증가) | 예제 기반 | 키 파일, 포트 판정, 시작 흐름, 키 복사, 실제 서버 프로세스, 서버 종료 |
| `test_launcher_properties.py` | 6 (3차에서 8로 증가) | 속성 기반 | WP-01~05 (포트 선택, 키 파일 왕복, 키 생성), 종료 대상 선택 |
| `test_ui_*.py` 4개 | 60 | 화면 (e2e) | `e2e-test-instructions.md` 참고 |
| **2차 추가 합계** | **137** | | |
| **전체 합계** | **298** (3차에서 26개 추가되어 **324**, 4차에서 19개 추가되어 **343**) | | |

- 속성 기반 테스트는 이제 두 파일이다: `test_properties.py`(API, 9개)와 `test_launcher_properties.py`(실행 로직, 6개). 시드 지정과 재현 방법은 위와 같다
- `test_launcher.py`는 실제 소켓을 열고 실제 서버 프로세스를 띄운다. 임의의 빈 포트와 임시 디렉터리를 쓰므로 실행 중인 서버와 실제 DB에 영향이 없다

## 4차 워크플로(등록 일자와 완료 일자)에서 추가된 테스트

| 파일 | 추가 수 | 종류 | 대상 |
|---|---|---|---|
| `test_migration.py` (신규) | 6 | 예제 5, 속성 1 | 이전 버전 DB에 `completed_at` 열 추가, 데이터 보존, 한 번만 추가, 되돌리기 호환 |
| `test_ui_dates.py` (신규) | 9 | 화면 (e2e) | 날짜 표시, 시간대, 미완료/예전 완료 행, 즉시 갱신, 줄 맞춤, 접근성 |
| `test_todos_api.py` | 2 | 예제 기반 | 완료 시각 유지와 갱신, `completed_at` 요청 거부 |
| `test_repository.py` | 1 | 예제 기반 | 완료 시각 기록과 삭제 |
| `test_serialization.py` | 1 | 예제 기반 | 완료 시각이 없으면 `null` |
| **4차 추가 합계** | **19** | | |

- `test_properties.py`는 개수가 같지만 상태 기반 모델이 `completed_at`을 추적하고, 불변식 하나(완료일 때만 완료 시각이 있음)가 더해졌다. 왕복 속성(P-02)은 확장된 생성기로 `completed_at`까지 검증한다
- `test_ui_dates.py`는 `pytest.mark.browser_context_args(timezone_id=...)`로 브라우저 시간대를 고정한다(기본 한국 시간, 한 테스트는 UTC)

