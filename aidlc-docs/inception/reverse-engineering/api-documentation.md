# API 문서

## REST API

기본 주소는 `http://127.0.0.1:8000`이다. 요청과 응답 본문은 JSON(`application/json`)이다.
`/todos` 아래의 모든 요청은 `X-API-Key` 헤더가 필요하다.

| 기능 | 메서드와 경로 | 인증 | 요청 | 성공 응답 |
|---|---|---|---|---|
| 추가 | `POST /todos` | 필요 | `{"title": 문자열}` | 201, Todo |
| 목록 조회 | `GET /todos` | 필요 | 쿼리 `completed=true` 또는 `false` (선택) | 200, `{"todos": [Todo, ...]}` 최신 순 |
| 단건 조회 | `GET /todos/<id>` | 필요 | - | 200, Todo |
| 완료 상태 변경 | `PATCH /todos/<id>` | 필요 | `{"completed": 불리언}` | 200, Todo |
| 삭제 | `DELETE /todos/<id>` | 필요 | - | 204, 본문 없음 |
| 상태 확인 | `GET /health` | 공개 | - | 200, `{"status": "ok"}` |

### Todo 표현
```json
{"id": 1, "title": "우유 사기", "completed": false, "created_at": "2026-10-12T05:38:00.676854Z"}
```

### 오류 응답
```json
{"error": {"code": "validation_error", "message": "사람이 읽을 수 있는 설명", "details": [{"field": "title", "reason": "too_long"}]}}
```

| HTTP | code | 상황 |
|---|---|---|
| 400 | `validation_error` | 검증 실패. `details`에 필드와 이유 |
| 401 | `unauthorized` | API 키 없음 또는 불일치 |
| 404 | `not_found` | 없는 항목, 삭제된 항목, 없는 경로 |
| 405 | `method_not_allowed` | 지원하지 않는 메서드 |
| 409 | `duplicate_title` | 같은 제목의 활성 항목 존재 |
| 413 | `payload_too_large` | 본문 16KB 초과 |
| 415 | `unsupported_media_type` | 본문이 JSON이 아님 |
| 429 | `rate_limited` | 요청 제한 초과, `Retry-After` 헤더 |
| 500 | `internal_error` | 예상하지 못한 오류 |
| 503 | `service_unavailable` | DB 사용 불가 |

`details`의 `reason`: `unknown_field`, `required`, `invalid_type`, `too_short`, `too_long`, `invalid_characters`, `invalid_value`, `invalid_json`.

### 모든 응답에 붙는 헤더
- `X-Request-ID`: 서버가 만든 요청 ID
- `X-Content-Type-Options: nosniff`
- `Cache-Control: no-store`
- CORS 헤더는 보내지 않는다. 다른 출처의 웹 페이지는 이 API를 호출할 수 없다

### 요청 제한
- 한 주소당 분당 60회 (모든 경로 공유)
- 인증 실패는 한 주소당 분당 10회. 초과하면 올바른 키로도 `/todos`가 최대 1분간 429

## 내부 API

### `todo_api.app`
- `create_app(config: Config | None = None) -> Flask`

### `todo_api.repository` (모두 첫 인자는 `sqlite3.Connection`)
- `create_todo(conn, title: str) -> Todo` - 중복이면 `DuplicateTitle`
- `list_todos(conn, completed: bool | None = None) -> list[Todo]`
- `get_todo(conn, todo_id: int) -> Todo | None`
- `set_completed(conn, todo_id: int, completed: bool) -> tuple[Todo | None, bool | None]` - (현재 Todo, 변경 전 값)
- `soft_delete(conn, todo_id: int) -> bool`

### `todo_api.validation`
- `normalize_title(value) -> str` - 실패 시 `FieldError(reason)`
- `validate_object(data, schema) -> dict` - 실패 시 `ValidationError(details)`
- 스키마: `CREATE_TODO_SCHEMA`, `UPDATE_TODO_SCHEMA`, `LIST_QUERY_SCHEMA`

### `todo_api.db`
- `init_db(db_path, timeout)`, `get_db()`, `close_db()`, `write_transaction(conn)`, `run_with_retry(operation, func)`

### `todo_api.backup`
- `backup_database(db_path, backup_dir, keep=7) -> Path`
- `restore_database(backup_path, db_path) -> Path | None`
- `verify_database(path) -> bool`, `list_backups(backup_dir) -> list[Path]`

## 데이터 모델

### Todo (테이블 `todos`)

| 필드 | 타입 | 검증 |
|---|---|---|
| `id` | 정수, 자동 증가 | 서버 부여 |
| `title` | 텍스트 | 앞뒤 공백 제거 후 1~200자, 제어 문자 불가. 활성 항목 사이에서 유일(영문 대소문자 무시) |
| `completed` | 0 또는 1 | 기본값 0 |
| `created_at` | ISO 8601 UTC 텍스트 | 서버 부여, 불변 |
| `deleted_at` | ISO 8601 UTC 텍스트 또는 NULL | 논리 삭제 시 기록. API 응답에 노출하지 않음 |

- **관계**: 없음

## 2차 워크플로(웹 화면)에서 추가된 것

### 화면 제공 경로 (인증 불필요)

| 주소 | 내용 | 콘텐츠 유형 |
|---|---|---|
| `GET /api_test` (끝에 `/`가 있어도 같음) | 화면 문서 | `text/html; charset=utf-8` |
| `GET /api_test/app.css` | 스타일 | `text/css; charset=utf-8` |
| `GET /api_test/app.js` | 스크립트 | `text/javascript; charset=utf-8` |
| `GET /api_test/<그 밖의 이름>` | 404 (공통 JSON 오류 형식) | `application/json` |

기존 엔드포인트 6개의 요청/응답 계약은 바뀌지 않았다.

### 모든 응답에 붙는 헤더 (갱신)
위의 "모든 응답에 붙는 헤더"에 다음이 더해졌다.
- `Content-Security-Policy`: 기본 차단, 같은 출처의 스크립트/스타일/API 호출만 허용
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

### 내부 API 추가
- `todo_api.security_headers.register_security_headers(app)`
- `todo_api.launcher`: `choose_port(states) -> Selection`, `probe_ports(key, windows_ports, ports) -> dict`, `read_key(path)`, `create_key_file(path)`, `run_start(project_root, effects)`, `run_copy_key(project_root, effects)`
