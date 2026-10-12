# 코드 구조

## 빌드 시스템
- **유형**: pip + venv (컴파일 없음)
- **설정**: `pyproject.toml`(메타데이터, pytest 설정), `requirements.txt`(실행), `requirements-dev.txt`(개발/테스트). 모든 버전 `==` 고정
- **실행 방식**: 패키지로 설치하지 않고 `PYTHONPATH=src`로 직접 실행

## 모듈 계층

```text
src/todo_api/
  server.py            -> app.py, config.py
  app.py               -> config, db, errors, logging_setup, rate_limit, routes
  routes/todos.py      -> auth, db, repository, validation, serialization, errors, logging_setup
  routes/health.py     -> db, errors
  auth.py              -> rate_limit, errors, logging_setup
  rate_limit.py        -> config
  repository.py        -> db, errors, serialization
  db.py                -> config, errors, logging_setup
  validation.py        -> errors
  errors.py            -> logging_setup
  logging_setup.py     -> config
  serialization.py     -> (없음)
  config.py            -> (없음)
  backup.py            -> config
```

순환 의존은 없다.

### 기존 파일 목록 (변경 후보)

애플리케이션:
- `src/todo_api/__init__.py` - 패키지, `create_app` 노출
- `src/todo_api/app.py` - 앱 팩토리. 새 라우트 묶음이나 정적 파일 제공을 추가할 때 수정 대상
- `src/todo_api/config.py` - 환경 변수와 설정 값
- `src/todo_api/auth.py` - `X-API-Key` 인증 훅
- `src/todo_api/rate_limit.py` - 요청 제한 구성
- `src/todo_api/validation.py` - 입력 스키마와 검증
- `src/todo_api/serialization.py` - Todo 표현
- `src/todo_api/repository.py` - Todo SQL
- `src/todo_api/db.py` - 연결, 스키마, 재시도
- `src/todo_api/errors.py` - 오류 클래스와 전역 처리기
- `src/todo_api/logging_setup.py` - 로깅, 요청 훅, 공통 응답 헤더(`nosniff`, `no-store`)
- `src/todo_api/routes/__init__.py` - 라우트 패키지
- `src/todo_api/routes/todos.py` - `/todos` 엔드포인트 5개
- `src/todo_api/routes/health.py` - `/health`
- `src/todo_api/server.py` - Waitress 진입점
- `src/todo_api/backup.py` - 백업/복원 명령줄 도구

테스트:
- `tests/conftest.py` - 픽스처, 이벤트 수집기, Hypothesis 프로필
- `tests/strategies.py` - 제너레이터
- `tests/test_validation.py`, `test_serialization.py`, `test_config.py`, `test_repository.py` - 단위 테스트
- `tests/test_todos_api.py`, `test_auth.py`, `test_rate_limit.py`, `test_errors.py`, `test_health.py` - API 테스트
- `tests/test_properties.py` - 속성 기반 테스트
- `tests/test_resilience.py`, `test_backup.py` - 복원력 테스트

설정과 문서:
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`
- `.github/workflows/ci.yml`
- `README.md`, `docs/coe-template.md`, `docs/resilience-drill-log.md`

## 디자인 패턴

| 패턴 | 위치 | 목적 |
|---|---|---|
| 앱 팩토리 | `app.py` | 설정을 주입해 테스트마다 독립된 앱 생성 |
| 블루프린트 단위 기본 거부 인증 | `routes/todos.py` | 묶음 전체에 인증 훅을 걸어 새 라우트도 자동 보호 |
| 선언적 스키마 검증 | `validation.py` | 엔드포인트별 허용 필드와 규칙을 한 곳에 선언 |
| 저장소 패턴 | `repository.py` | SQL을 한 모듈에 모으고 파라미터 바인딩만 사용 |
| 요청 단위 연결 | `db.py` | 요청마다 연결을 열고 종료 훅에서 닫음 |
| 제약 기반 중복 방지 | `db.py` 스키마 | 부분 유일 인덱스로 동시 요청에도 안전 |
| 1회 재시도 | `db.py` `run_with_retry` | 잠금 오류만 한 번 재시도 후 503 |
| 전역 오류 변환 | `errors.py` | 모든 오류를 공통 JSON 형식으로 |
| 구조화 로깅 | `logging_setup.py` | 이벤트 이름과 요청 ID가 있는 JSON 로그 |

## 핵심 의존성

| 의존성 | 버전 | 사용처 | 목적 |
|---|---|---|---|
| Flask | 3.1.3 | 전체 | 웹 프레임워크 |
| Flask-Limiter | 4.1.1 | `rate_limit.py` | 요청 제한 |
| limits | 5.8.0 | `rate_limit.py` | 한도 판정 (Flask-Limiter의 하위 의존성을 직접 사용) |
| Waitress | 3.0.2 | `server.py` | WSGI 서버 |
| sqlite3 | 표준 라이브러리 | `db.py`, `repository.py`, `backup.py` | 저장 |

## 2차 워크플로(웹 화면)에서 추가된 것

### 추가된 파일
- `src/todo_api/security_headers.py` - 모든 응답의 보안 헤더와 캐시 헤더 (기존에 `logging_setup.py`에 있던 헤더 두 개를 옮겨 옴)
- `src/todo_api/routes/web.py` - `/api_test` 화면 파일 제공 (고정 목록, 공개)
- `src/todo_api/web/index.html`, `app.css`, `app.js` - 화면
- `src/todo_api/launcher.py` - Windows 실행 파일이 호출하는 실행 로직
- `todo-start.bat`, `todo-copy-key.bat` - Windows 실행 파일
- `tests/test_security_headers.py`, `test_web_routes.py` - 서버 쪽 화면 테스트
- `tests/test_launcher.py`, `test_launcher_properties.py` - 실행 로직 테스트
- `tests/test_ui_key.py`, `test_ui_todos.py`, `test_ui_errors.py`, `test_ui_display.py` - 브라우저 테스트

### 모듈 계층에 더해진 의존
```text
app.py               -> security_headers, routes/web (추가)
routes/web.py        -> errors
security_headers.py  -> (없음)
launcher.py          -> config (서버는 별도 프로세스로 시작)
```

### 추가된 디자인 패턴

| 패턴 | 위치 | 목적 |
|---|---|---|
| 전 응답 보안 헤더 | `security_headers.py` | 헤더 설정을 한 곳에 모아 모든 응답에 적용 |
| 고정 목록 기반 파일 제공 | `routes/web.py` | 요청 경로를 파일 경로로 쓰지 않아 경로 탈출 차단 |
| 텍스트 전용 화면 갱신 | `web/app.js` | 서버 문자열을 텍스트로만 삽입 (XSS 방지) |
| 단일 호출 경로 | `web/app.js` `callApi` | 제한 시간과 실패 분류를 한 곳에서 처리 |
| 순수 계산과 부수 효과 분리 | `launcher.py` | 포트 선택 등을 네트워크 없이 테스트 |
