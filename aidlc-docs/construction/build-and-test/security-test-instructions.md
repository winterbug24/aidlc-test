# 보안 테스트 지침

Security Baseline 확장 규칙이 코드에서 지켜지는지 확인하는 절차다. 침투 테스트는 범위에 포함하지 않는다(로컬 전용).

## 1. 의존성 취약점 스캔 (SECURITY-10)

```bash
.venv/bin/python -m pip_audit -r requirements-dev.txt --no-deps --disable-pip
```

- **기대 결과**: `No known vulnerabilities found`
- `--no-deps`를 쓰면 해시 고정을 권장하는 경고 두 줄이 나온다. 모든 의존성이 `==`로 고정되어 있어 결과에는 영향이 없다
- 취약점이 나오면 해당 패키지를 수정 버전으로 올리고, 전체 테스트를 통과시킨 뒤 고정 파일을 갱신한다
- CI(`.github/workflows/ci.yml`)가 푸시마다 같은 스캔을 실행한다

## 2. 자동화된 보안 테스트

```bash
.venv/bin/python -m pytest tests/test_auth.py tests/test_rate_limit.py tests/test_errors.py \
  tests/test_validation.py tests/test_config.py tests/test_backup.py
```

| 규칙 | 확인 내용 | 테스트 |
|---|---|---|
| SECURITY-08 | 보호 라우트 5개 모두 키 없이 401, 잘못된 키 401, 인증이 검증보다 먼저, 인증 실패 시 자원 존재 여부 비노출, 실패한 요청은 데이터를 바꾸지 않음 | `test_auth.py` |
| SECURITY-08 | CORS 헤더 없음 | `test_errors.py` |
| SECURITY-11 | 전체 한도와 인증 실패 한도, 429와 `Retry-After` | `test_rate_limit.py` |
| SECURITY-05 | 타입, 길이, 제어 문자, 정의되지 않은 필드, 잘못된 JSON, 16KB 초과, 깊게 중첩된 JSON | `test_validation.py`, `test_todos_api.py`, `test_errors.py` |
| SECURITY-05 | SQL 조각이 든 제목이 데이터로만 저장됨 | `test_repository.py` |
| SECURITY-09, 15 | 500 응답에 예외 이름, 경로, 스택 트레이스 없음. DB 손상 시에도 내부 정보 없음 | `test_errors.py`, `test_resilience.py` |
| SECURITY-09, 12 | 키가 없거나 32자 미만이면 시작 거부, 설정 객체 출력에 키 없음 | `test_config.py` |
| SECURITY-03 | 로그에 API 키와 제목 본문 없음, 요청 ID 포함 | `test_auth.py`, `test_todos_api.py`, `test_errors.py` |
| SECURITY-13 | 생성/상태 변경/삭제 이벤트에 id와 전후 값 | `test_todos_api.py` |
| SECURITY-01 | DB와 백업 파일 600, 디렉터리 700 | `test_backup.py` |

## 3. 수동 확인

| 항목 | 방법 | 기대 |
|---|---|---|
| 하드코딩된 자격 증명 없음 | `grep -rniE "api[_-]?key\s*=\s*[\"'][A-Za-z0-9_-]{16,}" src tests` | 결과 없음 |
| 디버그 모드 꺼짐 | `grep -rn "debug" src` | `app.debug = False`만 있음 |
| 기본 바인딩 | `TODO_HOST` 없이 서버 실행 후 `ss -ltn \| grep 8000` | `127.0.0.1:8000` |
| 서버 정보 비노출 | `curl -s -i http://127.0.0.1:8000/health` | `Server` 헤더에 제품명과 버전 없음 |
| 버전 관리 제외 | `git status --short` | `.venv/`, `instance/`, `logs/`, `backups/`가 나타나지 않음 |

## 4. 운영 전제 (자동으로 확인할 수 없음)
- DB, 백업, 로그 파일이 있는 볼륨에 OS 디스크 암호화가 적용되어 있어야 한다 (SECURITY-01의 준수 전제)
- `TODO_HOST`를 루프백이 아닌 주소로 바꾸지 않는다. 바꾸면 통신이 암호화되지 않은 채 네트워크에 노출된다

## 2차 워크플로(웹 화면)에서 추가된 보안 확인

### 자동화된 테스트
```bash
.venv/bin/python -m pytest tests/test_security_headers.py tests/test_web_routes.py tests/test_launcher.py tests/test_ui_key.py tests/test_ui_todos.py -q
```

| 규칙 | 확인 내용 | 테스트 |
|---|---|---|
| SECURITY-04 | 보안 헤더 5종이 화면, API, 401, 404, 405, 409, 429, 500 응답 모두에 붙음. 정책에 `unsafe-inline`, `unsafe-eval`, 외부 출처 없음 | `test_security_headers.py` |
| SECURITY-04 | 화면 문서에 인라인 스크립트, 인라인 스타일, 인라인 이벤트 처리기, 외부 주소 없음 | `test_web_routes.py` |
| SECURITY-04 | 실제 브라우저에서 콘텐츠 보안 정책 위반 0건 | 모든 `test_ui_*.py` (공통 감시 장치) |
| SECURITY-05 | 목록 밖 이름과 경로 탈출 시도(`..`, 인코딩된 구분자, 역슬래시, `.env`)가 404 | `test_web_routes.py` |
| SECURITY-05 | 태그가 든 제목과 서버 오류 문구가 화면에 글자 그대로 표시되고 요소가 생기지 않음 | `test_ui_todos.py`, `test_ui_errors.py` |
| SECURITY-05 | 스크립트가 문자열을 마크업으로 넣는 기능(`innerHTML` 등)을 쓰지 않음 | `test_web_routes.py` |
| SECURITY-08 | 화면은 인증 없이 열리지만 `/todos`는 계속 401. 화면 파일에 데이터와 키 없음 | `test_web_routes.py` |
| SECURITY-08 | 키 없이는 화면에 목록이 보이지 않음. 서버가 받아들인 키만 저장 | `test_ui_key.py` |
| SECURITY-03 | 키가 주소, 화면 글자, 요청 주소에 없음. 스크립트에 콘솔 출력 없음 | `test_ui_key.py`, `test_web_routes.py` |
| SECURITY-11 | 화면 파일 요청도 요청 제한 대상. 실제 인증 실패 한도 동작 | `test_security_headers.py`, `test_ui_key.py` |
| SECURITY-12 | 실행 파일이 만든 키 파일 권한 600, 기존 키 파일 보존, 출력과 프로세스 인자에 키 없음 | `test_launcher.py` |

### 수동 확인 추가

| 항목 | 방법 | 기대 |
|---|---|---|
| 응답 헤더 | 서버 실행 후 `curl -s -D - -o /dev/null http://127.0.0.1:8000/api_test` | `Content-Security-Policy` 등 5종과 `Cache-Control: no-store` |
| 브라우저 개발자 도구 | 화면을 열고 F12의 콘솔 탭 확인 | 정책 위반("Refused to ...") 메시지 없음 |
| 키 저장 위치 | F12의 애플리케이션 탭에서 로컬 저장소 확인 | `todoApiKey` 한 항목만 있음. "키 지우기" 뒤에는 없음 |
| 프로세스 인자 | 실행 파일로 서버를 띄운 뒤 WSL에서 `ps -ef \| grep todo_api` | 명령줄에 키가 보이지 않음 |

### 수용한 위험 (자동으로 막을 수 없음)
- 브라우저 저장소의 키는 평문이다. 같은 Windows 계정의 프로그램이 읽을 수 있다
- 클립보드에 복사한 키는 Windows 클립보드 기록이 켜져 있으면 기록에 남는다
- 실행 파일은 WSL 안의 8000~8009번 포트에서 HTTP를 받는 프로그램에 키가 든 요청을 한 번 보낸다 (우리 서버인지 확인하려는 것). Windows 쪽 프로그램에는 보내지 않는다
