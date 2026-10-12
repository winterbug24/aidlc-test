# 코드 생성 요약 - todo-api

계획 문서: `aidlc-docs/construction/plans/todo-api-code-generation-plan.md` (13단계 모두 완료)

## 1. 생성한 파일

### 애플리케이션 코드 (`src/todo_api/`)

| 파일 | 논리 컴포넌트 | 내용 |
|---|---|---|
| `__init__.py` | - | 패키지, `create_app` 노출 |
| `config.py` | C-01 설정 | 환경 변수 6개, API 키 검증(없거나 32자 미만이면 시작 거부), 소유자 전용 파일/디렉터리 도우미 |
| `app.py` | C-02 앱 팩토리 | 설정을 받아 로깅, DB, 요청 훅, 요청 제한, 오류 처리기, 라우트를 조립 |
| `auth.py` | C-03 인증 | `X-API-Key` 상수 시간 비교, 실패 기록, 401 |
| `rate_limit.py` | C-04 요청 제한 | Flask-Limiter 전체 한도(분당 60회, 모든 라우트 공유)와 인증 실패 한도(분당 10회) |
| `validation.py` | C-05 검증 | 엔드포인트별 스키마, 제목 정규화, 모든 문제를 모아 보고 |
| `repository.py` | C-06 저장소 | Todo 생성/조회/상태 변경/논리 삭제 SQL (파라미터 바인딩) |
| `db.py` | C-07 DB 연결 관리 | 요청 단위 연결, WAL, 멱등 스키마 초기화, 잠금 시 1회 재시도 |
| `routes/todos.py` | C-08 할 일 라우트 | 보호 엔드포인트 5개, 변경 이벤트 기록 |
| `routes/health.py` | C-09 상태 확인 | 공개 엔드포인트, DB 읽기 확인 |
| `errors.py` | C-10 오류 처리 | 업무 오류, 공통 JSON 오류 형식, 전역 처리기 |
| `logging_setup.py` | C-11 로깅 | JSON 포매터, 표준 출력과 순환 파일, 요청 ID, 요청 로그, 공통 응답 헤더 |
| `serialization.py` | C-12 직렬화 | 저장소 행과 Todo 표현 변환 |
| `server.py` | C-13 서버 진입점 | Waitress 실행 (`python -m todo_api.server`) |
| `backup.py` | C-14 백업 도구 | 온라인 백업, 무결성 검사, 최근 7개 보관, 검증된 복원 (`python -m todo_api.backup`) |

### 테스트 (`tests/`)

| 파일 | 종류 | 내용 |
|---|---|---|
| `conftest.py` | 공용 | 임시 DB 앱 픽스처, 로그 이벤트 수집기, Hypothesis 프로필 |
| `strategies.py` | 공용 | 유효/무효 제목, Todo 등 재사용 제너레이터 |
| `test_validation.py`, `test_serialization.py`, `test_config.py` | 예제 기반 | 업무 로직 단위 테스트 |
| `test_repository.py` | 예제 기반 | 저장소 계층 단위 테스트 |
| `test_todos_api.py`, `test_auth.py`, `test_rate_limit.py`, `test_errors.py`, `test_health.py` | 예제 기반 | API 계층 테스트 |
| `test_properties.py` | 속성 기반 | P-01~P-09 (상태 기반 모델 테스트 포함) |
| `test_resilience.py`, `test_backup.py` | 복원력 | RT-01~07 (RT-08은 `test_config.py`) |

### 설정, CI, 문서

| 파일 | 내용 |
|---|---|
| `pyproject.toml` | 프로젝트 메타데이터, pytest 설정 |
| `requirements.txt` | 실행 의존성 15개를 `==`로 고정 (직접 3개 + 하위 12개) |
| `requirements-dev.txt` | 개발/테스트 의존성을 `==`로 고정 |
| `.gitignore` | 가상 환경, DB, 로그, 백업, 캐시 제외 |
| `.github/workflows/ci.yml` | C-15. 테스트와 취약점 스캔, 액션은 커밋 SHA로 고정 |
| `README.md` | 설치, 설정, 실행, API, 백업/복원, 문제 해결, 롤백, 보안 유의 사항 |
| `docs/coe-template.md` | 사후 분석 양식 |
| `docs/resilience-drill-log.md` | 복원 훈련 기록 양식 |

## 2. 요구사항 추적

| 요구사항 | 구현 | 테스트 |
|---|---|---|
| FR-01 할 일 추가 | `routes/todos.py` `create_todo`, `validation.py`, `repository.py` | `test_todos_api.py`, `test_properties.py` P-01, P-06, P-07 |
| FR-02 목록 조회 | `routes/todos.py` `list_todos`, `repository.py` | `test_todos_api.py`, P-03, P-05 |
| FR-03 단건 조회 | `routes/todos.py` `get_todo` | `test_todos_api.py`, P-01 |
| FR-04 완료 상태 변경 | `routes/todos.py` `update_todo`, `repository.set_completed` | `test_todos_api.py`, P-08 |
| FR-05 삭제 | `routes/todos.py` `delete_todo`, `repository.soft_delete` | `test_todos_api.py`, P-04 |
| FR-06 상태 확인 | `routes/health.py` | `test_health.py`, `test_resilience.py` RT-03 |

## 3. 검증 결과 (코드 생성 중 실행)

| 항목 | 결과 |
|---|---|
| 전체 테스트 (`pytest`) | 161개 통과, 약 11초. 시드를 바꿔 두 번 실행해 모두 통과 |
| 의존성 취약점 스캔 (`pip-audit`) | 알려진 취약점 없음 |
| 의존성 일관성 (`pip check`) | 문제 없음 |
| 실제 서버 구동 | Waitress로 실행해 추가, 조회, 401, 상태 확인, 검증 오류 응답 확인. DB와 로그 파일 권한 600 확인. 키 없이 실행하면 종료 코드 2 |
| GitHub Actions 워크플로 | 실행하지 않음 (로컬에서 실행할 수 없음). 첫 푸시 때 확인 필요 |

계획에서는 이 단계에서 가져오기와 수집만 확인하기로 했으나, 생성한 코드를 검증하기 위해 전체 테스트를 실행했다. 공식 결과 보고는 Build and Test 단계에서 한다.

## 4. 설계와 달라진 점

| 항목 | 내용 | 이유 |
|---|---|---|
| 검증 오류 이유 `invalid_json` 추가 | JSON으로 해석할 수 없는 본문은 `body` / `invalid_json`으로 알린다 | "객체가 아님"과 "JSON이 아님"을 구분하기 위해. 기능 설계 문서에 반영함 |
| 짝이 맞지 않는 서로게이트 문자 거부 | 제어 문자와 함께 `invalid_characters`로 거부 | 저장 시 인코딩 오류로 500이 나는 것을 막기 위해. 기능 설계 문서에 반영함 |
| 인증 실패 한도 구현 방식 | Flask-Limiter의 저장소와 한도 판정 기능을 인증 모듈에서 직접 호출 | 키를 비교하기 전에 막아야 대입 공격을 제한할 수 있고, 동작을 명확히 테스트할 수 있음 |
| 본문 크기 확인 시점 | 인증보다 먼저 확인 | NFR 설계의 요청 파이프라인 순서를 따름 |
| `created_at` 형식 | 마이크로초까지 포함 (`2026-10-12T05:38:00.676854Z`) | 문자열 정렬이 시간 순서와 같도록 자릿수 고정 |
| 취약점 스캔 명령 | `pip_audit -r requirements-dev.txt --no-deps --disable-pip` | 기본 방식은 임시 가상 환경을 만드는데, `ensurepip`가 없는 환경에서 실패함. 모든 의존성이 고정되어 있어 이 방식으로 충분함 |

## 5. 환경 관련 사항

- `.venv`는 pip 없이 만든 뒤 PyPA 공식 `get-pip.py`로 가상 환경 안에만 pip를 설치했다 (시스템 Python에 `ensurepip` 없음).
- `.venv`, `instance/`, `logs/`, `backups/`는 버전 관리에서 제외된다.

## 6. 확장 규칙 준수 요약 (Code Generation 단계)

### Security Baseline
| 규칙 | 상태 | 근거 |
|---|---|---|
| SECURITY-01 | 준수 | DB, 백업, 로그 파일 600, 디렉터리 700 (`test_backup.py`에서 검증). OS 디스크 암호화 전제는 README에 명시. 저장소 전송 구간은 로컬 파일이라 N/A |
| SECURITY-02 | N/A | 네트워크 중개 장치 없음 |
| SECURITY-03 | 준수 | `logging_setup.py`. 타임스탬프, 요청 ID, 레벨, 메시지 포함. 키와 제목 미기록을 테스트로 검증. 중앙 로그 서비스는 로컬 파일로 대체 |
| SECURITY-04 | N/A | HTML 제공 없음. `nosniff` 헤더는 추가 적용 |
| SECURITY-05 | 준수 | 모든 핸들러가 `validation.py` 스키마 사용, SQL은 전부 파라미터 바인딩, 제목 200자, 본문 16KB 상한 |
| SECURITY-06 | N/A | IAM 없음 |
| SECURITY-07 | 준수 | 기본 바인딩 127.0.0.1, 다른 주소로 바꾸면 경고 로그 |
| SECURITY-08 | 준수 | `/todos` 묶음 전체에 인증 훅, `/health`만 공개로 분리, CORS 미사용. 객체 수준 소유권은 단일 키라 N/A |
| SECURITY-09 | 준수 | 기본 자격 증명 없음, 디버그 꺼짐, 일반 오류 메시지, `Server` 헤더 제거, 지원 중인 버전 사용 |
| SECURITY-10 | 준수 | 전체 의존성 `==` 고정, pip-audit을 CI와 README 절차에 포함, CI 액션 SHA 고정. SBOM은 프로덕션 배포가 없어 N/A |
| SECURITY-11 | 준수 | 인증은 `auth.py`로 분리, 요청 제한 적용, 오용 시나리오는 기능 설계에 문서화하고 테스트로 검증 |
| SECURITY-12 | 준수 | 하드코딩된 자격 증명 없음(테스트 키도 실행마다 생성). 비밀번호/세션/MFA는 N/A |
| SECURITY-13 | 준수 | 변경 이벤트에 id와 전후 값 기록. 역직렬화는 JSON만 사용 |
| SECURITY-14 | N/A | 로컬 전용. 인증 실패와 요청 제한 초과는 로그 이벤트로 기록 |
| SECURITY-15 | 준수 | 전역 오류 처리기, 키 없으면 시작 거부, 요청 종료 시 연결 닫기, 실패 시 트랜잭션 롤백 |

### Resiliency Baseline
| 규칙 | 상태 | 근거 |
|---|---|---|
| RESILIENCY-01, 02, 03 | 준수 | 이전 단계에서 확정, 변경 없음 |
| RESILIENCY-04 | 준수 | CI 워크플로 작성, 롤백 절차와 직접 교체 방식 README에 문서화 |
| RESILIENCY-05 | 준수 | 구조화 로그와 이벤트 8종. 추적과 대시보드는 N/A |
| RESILIENCY-06 | 준수 | `/health`가 DB 읽기 확인, 실패 시 503 |
| RESILIENCY-07, 08, 09 | N/A | 로컬 전용, 배포 인프라 없음 |
| RESILIENCY-10 | 준수 | busy timeout 5초, 잠금 시 1회 재시도 후 503 |
| RESILIENCY-11, 12, 13 | 준수 | `backup.py`, README의 복원 절차와 복원 후 검증 |
| RESILIENCY-14 | 준수 | 자동화 테스트 RT-01~08, 복원 훈련 절차와 기록 양식 |
| RESILIENCY-15 | 준수 | README 문제 해결 절차, COE 양식 |

### Property-Based Testing (부분 적용)
| 규칙 | 상태 | 근거 |
|---|---|---|
| PBT-02 | 준수 | P-01(API 왕복), P-02(행과 JSON 왕복) |
| PBT-03 | 준수 | P-03~P-07 |
| PBT-07 | 준수 | `tests/strategies.py`에 도메인 제너레이터를 모아 재사용 |
| PBT-08 | 준수 | 축소 기본값 유지, 실패 시 재현 정보 출력, CI에서 시드를 로그에 남김 |
| PBT-09 | 준수 | Hypothesis 6.169.0을 `requirements-dev.txt`에 고정 |
| PBT-04, 06, 10 | 권고 (수행함) | P-08(멱등성), P-09(상태 기반 모델), 예제 기반과 속성 기반 테스트 파일 분리 |
