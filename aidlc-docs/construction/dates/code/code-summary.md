# 코드 요약: dates (4차 워크플로, 등록 일자와 완료 일자 표시)

요구사항: `aidlc-docs/inception/requirements/dates-requirements.md`
계획: `aidlc-docs/construction/plans/dates-code-generation-plan.md`

## 변경한 파일

| 파일 | 변경 | 요구사항 |
|---|---|---|
| `src/todo_api/db.py` | `SCHEMA`에 `completed_at TEXT` 추가. `migrate()` 신규: 쓰기 트랜잭션 안에서 `PRAGMA table_info`로 열 유무를 확인하고 없으면 `ALTER TABLE ... ADD COLUMN`. 추가했을 때만 `db_migrated` 로그 이벤트. `init_db()`가 스키마 생성 뒤 호출 | DFR-02, DNFR-01, 02 |
| `src/todo_api/serialization.py` | `Todo.completed_at: str \| None = None`. 행 변환, 행 역변환, API 표현에 반영 | DFR-03 |
| `src/todo_api/repository.py` | 조회 열에 `completed_at`. `set_completed()`는 값이 같으면 아무것도 쓰지 않고 현재 값을 돌려주며, 바뀔 때만 `completed`와 `completed_at`(완료면 현재 UTC, 해제면 NULL)을 함께 갱신 | DFR-01 |
| `src/todo_api/web/index.html` | 항목 템플릿의 체크 상자와 제목 사이에 날짜 묶음(`todo-dates`). 등록/완료 각각 `<time>`. 각 칸에 보이지 않는 크기 기준 글자(`등록 0000/00/00`)를 겹쳐 칸 폭을 고정 | DFR-04 |
| `src/todo_api/web/app.js` | `localDateParts()`: 서버 형식의 UTC 문자열을 정규식으로 확인하고 밀리초까지만 `Date`에 넘겨 브라우저 시간대의 연/월/일을 구함. 형식이 틀리면 `null`. `fillDate()`: `yyyy/mm/dd` 또는 `-`를 `textContent`로 넣고 `datetime`은 `yyyy-mm-dd`. `fillItem()`: 체크 상자 이름은 제목(`aria-labelledby`), 날짜는 설명(`aria-describedby`). 미완료면 완료 일자와 구분점에 `is-blank` 클래스 | DFR-04, 05, DNFR-05 |
| `src/todo_api/web/app.css` | `todo-body`(날짜와 제목, 좁으면 줄바꿈), `todo-dates`(0.875rem, `--muted`, 고정폭 숫자), 겹침 격자 칸, `is-blank`(자리는 남기고 글자만 숨김) | DFR-04, DNFR-06 |
| `README.md` | 할 일 필드 표, 예시 응답, 화면 사용법의 날짜 설명, 스키마 자동 추가와 업데이트 전 백업 안내 | DNFR-03 |
| 리버스 엔지니어링 문서 | `api-documentation.md`(Todo 표현, 데이터 모델), `architecture.md`(4차 변경 절), `code-quality-assessment.md`(마이그레이션 항목), 타임스탬프 | - |

## 테스트

| 파일 | 변경 | 종류 |
|---|---|---|
| `tests/test_migration.py` (신규) | 이전 버전 스키마의 DB를 만들어 열 추가와 데이터 보존, 기존 완료 행은 NULL, 두 번 실행해도 한 번만 추가되고 로그도 한 번, 새 DB, 이전된 DB 위의 API 동작, 이전 버전 SQL이 새 DB에서 동작(되돌리기). 속성: 임의의 기존 행 집합에서 이전 전후 기존 열 값이 같고 새 열은 모두 NULL | 예제 5 + 속성 1 (PBT-03) |
| `tests/test_ui_dates.py` (신규) | 한국 시간대에서의 날짜 경계(UTC 15:30 → 다음 날), UTC 시간대, 미완료 행, 예전 완료 행의 `완료 -`, 체크/해제 즉시 갱신, 제목 시작 위치가 모든 행에서 같음, 체크 상자의 이름과 설명, 날짜를 눌러도 완료 전환, 잘못된 날짜는 `-`이고 HTML로 해석되지 않음 | 브라우저 9 |
| `tests/test_todos_api.py` | 응답 필드 집합 갱신, 완료/해제 응답의 `completed_at`, 같은 값 재요청 시 유지와 해제 후 재완료 시 새 시각, `completed_at` 요청 거부 | 예제 (갱신 2, 추가 2) |
| `tests/test_repository.py` | 완료 시각 기록, 유지, 해제 | 예제 1 |
| `tests/test_serialization.py` | 기대값에 `completed_at`, NULL이면 API에서 `null` | 예제 (갱신 3, 추가 1) |
| `tests/strategies.py` | `utc_timestamps()` 분리. `todos()`가 완료 여부와 맞는 `completed_at`을 생성(미완료 → 없음, 완료 → 시각 또는 없음) | 생성기 (PBT-07) |
| `tests/test_properties.py` | 상태 기반 모델이 `completed_at`을 추적(같은 값이면 그대로, 완료면 시각이 등록 시각 이후, 해제면 NULL). 불변식 `completed_at_is_set_exactly_when_completed` 추가. 기존 왕복 속성(P-02)이 새 생성기로 `completed_at`까지 검증 | 속성 (PBT-02, 03) |

결과: 자동 테스트 343개 통과 (기존 324개 + 새 19개).

## 생성 중 고친 문제
- 미완료 행의 완료 일자를 `hidden` 속성으로 숨기려 했으나 전역 규칙 `[hidden] { display: none !important; }` 때문에 자리가 사라져 제목 위치가 어긋났다. 자리를 남기는 `is-blank` 클래스(`visibility: hidden`)로 바꿨다.

## 설계상 결정
- 칸 폭은 숫자 폭을 가정한 값이 아니라 보이지 않는 기준 글자로 정한다. 글꼴이 달라도 모든 행의 제목 시작 위치가 같다.
- 체크 상자의 접근 가능한 이름은 그대로 제목이다(기존 테스트와 화면 낭독기 사용 방식 유지). 날짜는 설명으로 읽힌다.
- 화면의 날짜 변환은 JS 속성 기반 테스트 도구를 들이지 않고 브라우저 예제 테스트로 경계값(시간대 경계, 형식 오류)을 확인한다. PBT 부분 적용 모드에서 강제 대상인 왕복과 불변식은 Python 쪽에서 속성 기반으로 검증한다.

## 변경 요청 반영 (2026-10-14)
사용자 요청: 날짜를 두 줄로, 내용 칸을 조금 넓게, 테스트는 최소한으로.

- `index.html`: 구분점(`·`) 제거
- `app.js`: 구분점 처리 줄 제거
- `app.css`: `.todo-dates`를 세로 배치(`flex-direction: column`)로 바꿔 등록 일자 아래에 완료 일자. `.page` 최대 폭 42rem → 48rem(입력 칸과 제목 영역이 넓어짐). 제목 기본 폭 12rem → 10rem(좁은 화면에서 제목이 날짜 옆에 더 오래 머묾)
- `tests/test_ui_dates.py`: 구분점 확인을 "완료 일자가 등록 일자 아래 줄" 확인으로 교체
- 테스트: 지시에 따라 `test_ui_dates.py`(9개)만 실행, 통과. 전체 테스트는 다시 돌리지 않음

