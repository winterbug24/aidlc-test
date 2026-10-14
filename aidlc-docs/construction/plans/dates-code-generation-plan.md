# 코드 생성 계획: dates (4차 워크플로, 등록 일자와 완료 일자 표시)

이 계획이 4차 워크플로 Code Generation의 유일한 기준이다. 요구사항: `aidlc-docs/inception/requirements/dates-requirements.md`.

## 유닛 맥락
- **유닛**: `dates` (단일 유닛, 기존 `todo_api` 패키지 안의 변경)
- **작업 공간 루트**: `/home/winterbug/aidlc-test` (애플리케이션 코드는 `src/todo_api`, 테스트는 `tests/`)
- **의존**: 없음 (새 라이브러리 없음)
- **계약 변경**: 할 일 표현에 `completed_at`(UTC ISO 8601 문자열 또는 `null`) 추가. 요청 형식 변경 없음
- **소유 엔티티**: `todos` 테이블에 `completed_at TEXT NULL` 열 추가
- **기준선**: 변경 전 자동 테스트 324개 통과 (2026-10-14 확인)

## 테스트할 속성 (PBT-01 권고, PBT-02/03/07 강제)

| 속성 | 범주 | 대상 |
|---|---|---|
| 행 → Todo → 행 왕복 (completed_at 포함, NULL 포함) | Round-trip (PBT-02) | `serialization` |
| 완료 상태 변경 후 `completed`와 `completed_at`의 일관성: 완료면 시각 있음, 미완료면 NULL | Invariant (PBT-03) | `repository.set_completed` (기존 상태 기반 속성 테스트 확장) |
| 이전을 여러 번 실행해도 결과가 같고 기존 데이터가 보존됨 | Invariant (PBT-03) | `db.init_db` |
| 화면 날짜 변환: 유효한 UTC 시각은 항상 `yyyy/mm/dd` 형식이며 브라우저 시간대의 날짜와 같음 | Invariant | `app.js` 날짜 변환 (브라우저 테스트의 예제 기반 검증, JS 속성 테스트 프레임워크는 도입하지 않음) |

생성기는 `tests/strategies.py`의 `todos()`를 확장한다(PBT-07).

## 단계

### Step 1: 데이터 계층 - 스키마와 이전 (DFR-02, DNFR-01, 02)
- [x] `src/todo_api/db.py`: `SCHEMA`에 `completed_at TEXT` 추가(새 DB). 기존 테이블에 열이 없으면 `ALTER TABLE ... ADD COLUMN`으로 추가하는 이전 함수를 `init_db`에서 같은 연결로 호출. 이전은 쓰기 트랜잭션 하나에서 수행하고 이전 결과를 로그 이벤트로 남김

### Step 2: 데이터 계층 - Todo와 변환 (DFR-03)
- [x] `src/todo_api/serialization.py`: `Todo`에 `completed_at: str | None = None` 추가. `todo_from_row`, `todo_to_row`, `todo_to_dict`에 반영

### Step 3: 저장소 - 완료 시각 기록 (DFR-01)
- [x] `src/todo_api/repository.py`: 조회 열 목록에 `completed_at` 추가. `set_completed`가 값이 바뀔 때만 완료면 현재 UTC 시각, 해제면 NULL을 기록하고 결과 Todo에 반영. 새로 추가한 할 일은 `completed_at=None`

### Step 4: API 계층 확인 (DFR-03, DNFR-04)
- [x] `src/todo_api/routes/todos.py`: 직렬화를 통해 응답에 자동 반영되는지 확인. 요청 스키마(`validation.py`)는 바꾸지 않아 `completed_at`을 보내면 기존처럼 `unknown_field`로 거부됨을 확인

### Step 5: 웹 화면 (DFR-04, 05, DNFR-05, 06)
- [x] `src/todo_api/web/index.html`: 템플릿의 체크 상자와 제목 사이에 날짜 묶음(`todo-dates`) 추가. 등록/완료 각각 `<time>` 요소
- [x] `src/todo_api/web/app.js`: UTC ISO 문자열을 브라우저 시간대의 `yyyy/mm/dd`로 바꾸는 함수, 형식이 틀리면 `-`. `fillItem`에서 등록 일자, 완료 일자(완료+시각 → 날짜, 완료+시각 없음 → `-`, 미완료 → 글자 없음, 자리 유지) 채우기. `textContent`와 `dateTime` 속성만 사용
- [x] `src/todo_api/web/app.css`: 날짜 묶음 스타일(작은 글씨, `--muted` 색, 고정폭 숫자, 줄바꿈 허용, 완료 행의 취소선이 날짜에는 적용되지 않음)

### Step 6: 테스트 (DNFR-07, 08, PBT-02, 03, 07, 08, 09)
- [x] 기존 테스트 기대값 갱신: `test_serialization.py`, `test_todos_api.py`의 필드 집합
- [x] `tests/strategies.py`: `todos()`가 `completed`와 일관된 `completed_at`(완료면 시각 또는 NULL, 미완료면 NULL)을 만들도록 확장
- [x] 이전 테스트(`test_repository.py` 또는 새 파일): 열 없는 옛 DB를 만들어 `init_db` 후 열 추가, 데이터 보존, 기존 완료 행의 NULL, 두 번 실행해도 안전
- [x] 저장소/API 테스트: 완료 시 시각 기록, 해제 시 NULL, 같은 값 재요청 시 시각 유지, 새 할 일은 NULL, `completed_at` 요청 거부
- [x] 속성 기반 테스트(`test_properties.py`): 왕복(completed_at 포함), 완료 상태 변경 순서 뒤 일관성 불변식
- [x] 브라우저 테스트(`test_ui_dates.py` 신규): 등록 일자 표시, 완료/미완료/완료-시각없음 세 경우, 체크/해제 시 즉시 갱신, 시간대 경계(UTC 15:00 이후 → 한국 시간 다음 날), 줄 맞춤(제목 시작 위치 동일), 날짜가 HTML로 해석되지 않음

### Step 7: 문서
- [x] `README.md`: API 표와 예시의 응답에 `completed_at`, 화면 사용법에 날짜 표시, 업데이트 전 백업 안내(DNFR-03)
- [x] 리버스 엔지니어링 문서 갱신: `api-documentation.md`, 그 밖에 스키마나 화면을 설명하는 문서
- [x] `aidlc-docs/construction/dates/code/code-summary.md` 작성

### Step 8: 실제 DB 백업과 서버 시작
- [x] 실제 DB(`instance/todo.db`)를 백업 도구로 백업
- [x] `todo_api.launcher start`(todo-start.bat과 같은 경로)로 서버 시작, 이전 결과와 화면 응답 확인

## 추적
| 요구사항 | 단계 |
|---|---|
| DFR-01 | 3, 6 |
| DFR-02 | 1, 6, 8 |
| DFR-03 | 2, 4, 6 |
| DFR-04 | 5, 6 |
| DFR-05 | 5, 6 |
| DNFR-01~03 | 1, 7, 8 |
| DNFR-04 | 4, 6 |
| DNFR-05, 06 | 5, 6 |
| DNFR-07, 08 | 6 |
