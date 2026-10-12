# To-Do 관리 REST API

Flask와 SQLite로 만든 할 일 관리 API다. 할 일 추가, 조회, 완료 상태 변경, 삭제를 제공한다.
로컬 PC에서 한 사람이 쓰는 용도로 설계했다.

## 요구 사항

- Python 3.12
- Linux/WSL 또는 Windows (서버는 Waitress를 사용한다)

## 설치

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Ubuntu/WSL에서 `python3 -m venv`가 `ensurepip` 오류로 실패하면 먼저 `sudo apt install python3.12-venv`를 실행한다.

## 설정

환경 변수로 설정한다. `TODO_API_KEY`만 필수다.

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `TODO_API_KEY` | 예 | 없음 | API 키. 32자 이상. 없거나 짧으면 서버가 시작을 거부한다 |
| `TODO_DB_PATH` | 아니오 | `instance/todo.db` | SQLite 파일 경로 |
| `TODO_LOG_DIR` | 아니오 | `logs` | 로그 파일 디렉터리 |
| `TODO_BACKUP_DIR` | 아니오 | `backups` | 백업 파일 디렉터리 |
| `TODO_HOST` | 아니오 | `127.0.0.1` | 바인딩 주소 |
| `TODO_PORT` | 아니오 | `8000` | 포트 |

상대 경로는 프로젝트 루트 기준이다.

API 키 만들기:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

키는 소스 코드나 저장소에 넣지 않는다. 셸에서 `export TODO_API_KEY=...`로 설정한다.

## 실행

```bash
export TODO_API_KEY="만든 키"
PYTHONPATH=src .venv/bin/python -m todo_api.server
```

DB 파일과 테이블은 처음 실행할 때 자동으로 만들어진다.

## API

`/todos` 아래의 모든 요청은 `X-API-Key` 헤더가 필요하다. `/health`만 인증 없이 호출할 수 있다.
요청과 응답 본문은 JSON이다.

| 기능 | 메서드와 경로 | 요청 | 성공 응답 |
|---|---|---|---|
| 추가 | `POST /todos` | `{"title": "문자열"}` | 201, 할 일 |
| 목록 조회 | `GET /todos` | 쿼리 `completed=true` 또는 `false` (선택) | 200, `{"todos": [...]}` 최신 순 |
| 단건 조회 | `GET /todos/<id>` | - | 200, 할 일 |
| 완료 상태 변경 | `PATCH /todos/<id>` | `{"completed": true}` 또는 `false` | 200, 할 일 |
| 삭제 | `DELETE /todos/<id>` | - | 204, 본문 없음 |
| 상태 확인 | `GET /health` | - | 200, `{"status": "ok"}` |

### 사용 예시

```bash
KEY="$TODO_API_KEY"
BASE="http://127.0.0.1:8000"

# 추가
curl -s -X POST "$BASE/todos" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" -d '{"title": "우유 사기"}'
# {"id":1,"title":"우유 사기","completed":false,"created_at":"2026-10-12T05:38:00.676854Z"}

# 목록 조회, 미완료만 조회
curl -s "$BASE/todos" -H "X-API-Key: $KEY"
curl -s "$BASE/todos?completed=false" -H "X-API-Key: $KEY"

# 단건 조회
curl -s "$BASE/todos/1" -H "X-API-Key: $KEY"

# 완료 처리, 완료 취소
curl -s -X PATCH "$BASE/todos/1" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" -d '{"completed": true}'
curl -s -X PATCH "$BASE/todos/1" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" -d '{"completed": false}'

# 삭제
curl -s -X DELETE "$BASE/todos/1" -H "X-API-Key: $KEY"

# 상태 확인
curl -s "$BASE/health"
```

### 동작 규칙

- **제목**: 앞뒤 공백을 제거해 저장한다. 1~200자여야 하고 제어 문자(줄바꿈, 탭 등)는 넣을 수 없다. `<`, `>` 같은 문자는 그대로 저장한다.
- **제목 중복**: 삭제되지 않은 할 일 중에 같은 제목이 있으면 409로 거부한다. 영문 대소문자는 구분하지 않는다(`Buy milk`와 `buy milk`는 중복). 완료된 할 일도 비교 대상이다.
- **정의되지 않은 필드**: 요청 본문이나 쿼리에 정의되지 않은 필드가 있으면 400으로 거부하고 필드 이름을 알려 준다.
- **삭제**: 논리 삭제다. 삭제한 할 일은 어떤 조회에도 나오지 않고 복구할 수 없지만 DB에는 행이 남는다. 삭제 후에는 같은 제목을 다시 등록할 수 있다.
- **완료 상태 변경**: 같은 값으로 다시 요청해도 오류 없이 현재 상태를 돌려준다.

### 오류 응답

모든 오류는 같은 형식이다. `message`는 화면에 그대로 보여 줄 수 있는 설명이다.

```json
{"error": {"code": "validation_error", "message": "요청에 허용되지 않는 필드가 있습니다.", "details": [{"field": "priority", "reason": "unknown_field"}]}}
```

| HTTP | code | 상황 |
|---|---|---|
| 400 | `validation_error` | 본문/쿼리 검증 실패. `details`에 필드와 이유가 들어 있다 |
| 401 | `unauthorized` | API 키 없음 또는 불일치 |
| 404 | `not_found` | 없는 할 일, 삭제된 할 일, 없는 경로 |
| 405 | `method_not_allowed` | 지원하지 않는 메서드 |
| 409 | `duplicate_title` | 같은 제목의 할 일이 이미 있음 |
| 413 | `payload_too_large` | 본문이 16KB 초과 |
| 415 | `unsupported_media_type` | 본문이 `application/json`이 아님 |
| 429 | `rate_limited` | 요청 제한 초과. `Retry-After` 헤더 참고 |
| 500 | `internal_error` | 예상하지 못한 오류. 상세는 로그에만 남는다 |
| 503 | `service_unavailable` | DB를 쓸 수 없음. `Retry-After` 헤더 참고 |

`details`의 `reason` 값: `unknown_field`, `required`, `invalid_type`, `too_short`, `too_long`, `invalid_characters`, `invalid_value`, `invalid_json`.

### 요청 제한

- 한 주소에서 분당 60회까지 호출할 수 있다. 모든 경로가 이 한도를 함께 쓴다.
- 인증 실패는 한 주소에서 분당 10회까지다. 이 한도를 넘으면 올바른 키를 보내도 최대 1분 동안 `/todos` 요청이 429로 거부된다.
- 서버를 다시 시작하면 카운터가 초기화된다.

## 로그

JSON 형식으로 한 줄에 한 이벤트를 표준 출력과 `logs/todo-api.log`에 남긴다. 파일은 5MB마다 순환하고 최근 5개를 보관한다.
모든 응답에는 `X-Request-ID` 헤더가 있고, 같은 값이 로그의 `request_id`에 들어 있어 요청 하나의 로그를 찾을 수 있다.

주요 이벤트: `request`, `todo_created`, `todo_completion_changed`, `todo_deleted`, `auth_failed`, `rate_limited`, `db_retry`, `unhandled_error`.
제목 내용과 API 키는 로그에 남기지 않는다.

## 백업과 복원

DB는 WAL 모드로 동작해 `todo.db-wal`, `todo.db-shm` 보조 파일이 생긴다. DB 파일을 직접 복사하지 말고 아래 도구를 사용한다.

```bash
# 백업 (서버 실행 중에도 가능). backups/ 에 만들고 최근 7개만 보관한다
PYTHONPATH=src .venv/bin/python -m todo_api.backup backup

# 백업 목록
PYTHONPATH=src .venv/bin/python -m todo_api.backup list

# 복원
PYTHONPATH=src .venv/bin/python -m todo_api.backup restore backups/todo-<시각>.db
```

복원 절차:

1. 서버를 중지한다.
2. `restore` 명령을 실행한다. 백업 파일이 무결성 검사를 통과하지 못하면 복원을 거부하고 현재 DB는 그대로 둔다.
3. 서버를 시작한다.
4. `curl -s http://127.0.0.1:8000/health`가 `{"status":"ok"}`인지 확인하고 목록을 조회해 데이터를 확인한다.

복원 직전의 DB는 `instance/todo.db.before-restore-<시각>` 파일로 남는다. 확인이 끝나면 지워도 된다.

백업은 수동 실행이다. 마지막 백업 이후의 변경은 복원할 수 없으므로 필요한 만큼 자주 실행한다.

### 복원 훈련

분기에 한 번, 그리고 DB 스키마를 바꾸는 변경을 적용하기 전에 위 복원 절차를 실제로 수행한다. 소요 시간과 결과를 `docs/resilience-drill-log.md`에 기록한다.

## 테스트와 취약점 스캔

```bash
.venv/bin/python -m pip install -r requirements-dev.txt

# 전체 테스트 (예제 기반 + 속성 기반)
.venv/bin/python -m pytest

# 속성 기반 테스트를 같은 시드로 재현
.venv/bin/python -m pytest --hypothesis-seed=12345

# 의존성 취약점 스캔
.venv/bin/python -m pip_audit -r requirements-dev.txt --no-deps --disable-pip
```

GitHub에 푸시하면 `.github/workflows/ci.yml`이 같은 테스트와 스캔을 실행한다. 실행 로그에 Hypothesis 시드가 출력된다.

의존성 버전을 바꿀 때는 새 버전을 설치하고, 전체 테스트와 취약점 스캔을 통과한 뒤 `requirements.txt`와 `requirements-dev.txt`의 고정 버전을 갱신한다.

## 문제 해결

문제가 생기면 아래 순서로 확인한다.

1. **상태 확인**: `curl -s -i http://127.0.0.1:8000/health`
   - 연결이 안 되면 서버가 떠 있지 않은 것이다. 실행한 터미널의 출력을 확인한다. `설정 오류`가 보이면 환경 변수를 고친다.
   - 503이면 DB 파일을 읽을 수 없는 것이다. 4번으로 간다.
2. **로그 확인**: `logs/todo-api.log`에서 `"level": "ERROR"` 또는 `"event": "unhandled_error"`를 찾는다. 응답의 `X-Request-ID` 값으로 해당 요청의 로그를 찾을 수 있다.
3. **재시작**: 서버를 중지하고 다시 실행한다.
4. **백업 복원**: DB가 손상되었으면 위의 복원 절차를 따른다.
5. **기록**: 원인과 조치를 `docs/coe-template.md` 양식으로 남긴다.

| 증상 | 원인과 조치 |
|---|---|
| 401이 계속 나온다 | `X-API-Key` 헤더 값이 서버의 `TODO_API_KEY`와 같은지 확인한다 |
| 올바른 키인데 429가 나온다 | 인증 실패 한도를 넘었다. 1분 기다린다 |
| 503과 `Retry-After`가 나온다 | 다른 프로그램이 DB 파일을 잠그고 있다. DB 파일을 열어 둔 도구를 닫는다 |
| 응답이 10초 가까이 걸린다 | DB 잠금 대기(5초)와 재시도 1회 때문이다. 위와 같이 조치한다 |

## 롤백

변경 후 문제가 생기면 이전 버전으로 되돌린다.

```bash
# 서버 중지 후
git checkout <이전 커밋 또는 태그>
.venv/bin/python -m pip install -r requirements.txt
# 서버 시작, /health 확인
```

DB 스키마를 바꾸는 변경을 적용할 때는 먼저 백업을 만든다. 되돌릴 때는 코드를 되돌린 뒤 그 백업으로 복원한다.

## 보안 유의 사항

- **바인딩 주소**: 기본값 `127.0.0.1`은 같은 PC에서만 접속할 수 있다. `TODO_HOST`를 바꾸면 네트워크의 다른 기기가 접속할 수 있고, 통신은 암호화되지 않는다(HTTP).
- **저장 데이터 암호화**: SQLite 파일 자체는 암호화하지 않는다. DB, 백업, 로그 파일은 소유자만 읽을 수 있는 권한으로 만들어지며, 디스크 암호화(BitLocker, LUKS 등)가 적용된 볼륨에 두는 것을 전제로 한다.
- **제목의 HTML 문자**: 제목은 받은 그대로 저장하고 JSON으로만 돌려준다. 이 값을 웹 화면에 표시하는 클라이언트는 HTML 이스케이프를 직접 해야 한다.
- **단일 프로세스**: 요청 제한 카운터가 프로세스 메모리에 있다. 서버를 여러 프로세스로 띄우는 구성은 지원하지 않는다.

## 프로젝트 구조

```text
src/todo_api/      애플리케이션 코드
tests/             테스트 (예제 기반, 속성 기반, 복원력)
docs/              사후 분석 양식, 복원 훈련 기록
aidlc-docs/        요구사항과 설계 문서
```
