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
