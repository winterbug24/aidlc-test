# 통합 테스트 지침

## 목적
이 프로젝트는 유닛이 하나(`todo-api`)라 유닛 사이의 통합은 없다. 여기서 통합 테스트는 유닛 안의 계층(HTTP 라우트, 인증, 요청 제한, 검증, 저장소, SQLite, 로깅)이 함께 올바르게 동작하는지 확인하는 것이다.

## 자동화된 통합 테스트

별도 서비스를 띄울 필요가 없다. Flask 테스트 클라이언트가 실제 앱과 실제 SQLite 파일(임시)을 사용한다.

```bash
.venv/bin/python -m pytest tests/test_todos_api.py tests/test_auth.py tests/test_rate_limit.py \
  tests/test_errors.py tests/test_health.py tests/test_properties.py \
  tests/test_resilience.py tests/test_backup.py
```

### 시나리오

| 시나리오 | 검증 내용 | 테스트 |
|---|---|---|
| 라우트 → 검증 → 저장소 → SQLite | 요청이 검증을 거쳐 DB에 반영되고 같은 값이 조회된다 | `test_todos_api.py`, P-01 |
| 인증 → 라우트 | 키 없이는 어떤 보호 라우트도 실행되지 않고 데이터가 바뀌지 않는다 | `test_auth.py` |
| 요청 제한 → 인증 → 라우트 | 한도 초과 시 429, 인증 실패만 별도 한도를 소모한다 | `test_rate_limit.py` |
| 저장소 → DB 제약 | 중복 제목이 유일 인덱스로 막히고 409로 변환된다 | `test_todos_api.py`, P-06 |
| 오류 처리기 → 모든 계층 | 어느 계층의 오류든 공통 JSON 형식으로 나가고 내부 정보가 없다 | `test_errors.py`, RT-04 |
| 라우트 → 로깅 | 요청 ID가 응답 헤더와 로그에 같은 값으로 들어간다 | `test_errors.py` |
| DB 잠금 → 재시도 → 응답 | 잠금 시 1회 재시도 후 503 | RT-01, RT-02 |
| 백업 도구 → DB → 앱 | 백업으로 복원한 뒤 앱이 백업 시점 데이터를 제공한다 | RT-05, RT-06, RT-07 |
| 임의의 동작 순서 | 추가/변경/삭제를 무작위로 섞어도 API 결과가 모델과 일치한다 | P-09 |

- **기대 결과**: 모두 통과
- **정리**: 필요 없음. 임시 디렉터리는 자동으로 지워진다

## 실제 서버로 확인 (수동)

Waitress 서버, 실제 HTTP, 백업 도구를 함께 확인한다. 임시 디렉터리를 쓰므로 실제 데이터에 영향이 없다.

### 1. 서버 시작
```bash
D=$(mktemp -d)
export TODO_API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export TODO_DB_PATH=$D/todo.db TODO_LOG_DIR=$D/logs TODO_BACKUP_DIR=$D/backups TODO_PORT=8766
export PYTHONPATH=src
.venv/bin/python -m todo_api.server &
B=http://127.0.0.1:8766; H="X-API-Key: $TODO_API_KEY"; J="Content-Type: application/json"
```

### 2. 단계와 기대 결과

| 단계 | 명령 | 기대 |
|---|---|---|
| 1 | `curl -s -i $B/health` | 200 |
| 2 | `curl -s -i -X POST $B/todos -H "$H" -H "$J" -d '{"title":"우유 사기"}'` | 201 |
| 3 | 같은 요청을 제목 앞뒤에 공백을 넣어 다시 | 409 |
| 4 | `curl -s -i -X PATCH $B/todos/1 -H "$H" -H "$J" -d '{"completed":true}'` | 200 |
| 5 | `curl -s "$B/todos?completed=true" -H "$H"` | 1번 항목만 |
| 6 | `.venv/bin/python -m todo_api.backup backup` | `백업 완료` |
| 7 | `curl -s -i -X DELETE $B/todos/1 -H "$H"` | 204 |
| 8 | `curl -s -i $B/todos/1 -H "$H"` | 404 |
| 9 | `curl -s -i $B/todos` (키 없음) | 401 |
| 10 | 서버 중지 후 `.venv/bin/python -m todo_api.backup restore $D/backups/todo-*.db` | `복원 완료` |
| 11 | 서버 다시 시작 후 `curl -s $B/todos/1 -H "$H"` | 1번 항목이 완료 상태로 돌아옴 |

### 3. 로그 확인
```bash
cat $D/logs/todo-api.log          # 한 줄에 JSON 하나
grep -c "$TODO_API_KEY" $D/logs/todo-api.log   # 0이어야 한다
```

### 4. 정리
```bash
kill %1
rm -rf $D
```

## 2차 워크플로(웹 화면)에서 추가된 통합 지점

화면과 실행 파일이 더해지면서 통합 지점이 늘었다. 자동화된 것과 수동 확인이 필요한 것을 나눈다.

| 통합 지점 | 검증 내용 | 방법 |
|---|---|---|
| 화면 스크립트 → 기존 API | 화면의 추가, 체크, 삭제, 필터가 실제 서버와 실제 DB에 반영된다 | 자동: `test_ui_todos.py` (실제 서버와 실제 브라우저) |
| 화면 → 인증 | 키 없이는 목록이 보이지 않고, 틀린 키와 바뀐 키를 구분해 안내한다 | 자동: `test_ui_key.py` |
| 화면 → 요청 제한 | 실제 인증 실패 한도에 걸리면 올바른 키도 거부되고 화면이 이를 안내한다 | 자동: `test_ui_key.py`의 실제 한도 테스트 |
| 화면 라우트 → 보안 헤더 → 브라우저 | 콘텐츠 보안 정책 아래에서 화면이 위반 없이 동작한다 | 자동: 모든 화면 테스트가 정책 위반과 스크립트 오류 0건을 확인 |
| 실행 로직 → 서버 프로세스 | 키를 환경 변수로 받아 서버가 뜨고, 응답 확인 후 정리된다 | 자동: `test_launcher.py`의 실제 서버 프로세스 테스트 |
| 실행 로직 → 실행 중인 서버 식별 | 실제 앱은 우리 서버로, 다른 프로그램과 닫힌 포트는 아닌 것으로 판정한다 | 자동: `test_launcher.py` |
| 배치 파일 → WSL → 실행 로직 | 배치 파일이 자기 위치에서 경로를 알아내 실행 로직을 호출한다 | 수동: `e2e-test-instructions.md`. Code Generation 중 명령 해석기로 한 번 확인함 |
| 실행 로직 → Windows 클립보드, 브라우저 | 키가 클립보드에 들어가고 브라우저가 열린다 | 수동: `e2e-test-instructions.md`. 클립보드는 Code Generation 중 확인함 |
