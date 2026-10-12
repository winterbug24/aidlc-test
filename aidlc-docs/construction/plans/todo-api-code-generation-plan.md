# Code Generation 계획 - todo-api

이 문서는 Code Generation의 단일 기준 문서다. 생성 단계에서는 여기에 적힌 단계만, 적힌 순서대로 수행한다.

## 1. 유닛 컨텍스트

| 항목 | 내용 |
|---|---|
| 유닛 | `todo-api` (단일 유닛, 다른 유닛/서비스 의존 없음) |
| 프로젝트 유형 | Greenfield 단일 유닛 |
| 워크스페이스 루트 | `/home/winterbug/aidlc-test` |
| 코드 위치 | 워크스페이스 루트의 `src/`, `tests/` (aidlc-docs/ 안에는 코드를 두지 않음) |
| 소유 데이터 | `todos` 테이블 (SQLite) |
| 외부 인터페이스 | REST API 6개 엔드포인트 (기능 설계 `business-logic-model.md` 3장) |
| 입력 문서 | 요구사항, 기능 설계 3종, NFR 요구사항 2종, NFR 설계 2종 |

### 요구사항 추적 (User Stories를 건너뛰었으므로 기능 요구사항 기준)

- [x] FR-01 할 일 추가 - 단계 4, 5, 6, 7, 9
- [x] FR-02 할 일 목록 조회 - 단계 4, 5, 6, 7, 9
- [x] FR-03 할 일 단건 조회 - 단계 5, 6, 7, 9
- [x] FR-04 완료 상태 변경 - 단계 4, 5, 6, 7, 9
- [x] FR-05 할 일 삭제(논리 삭제) - 단계 5, 6, 7, 9
- [x] FR-06 상태 확인 - 단계 7, 9

## 2. 생성할 파일 구조

```text
aidlc-test/
  .github/workflows/ci.yml
  .gitignore
  README.md
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  docs/
    coe-template.md
    resilience-drill-log.md
  src/todo_api/
    __init__.py
    app.py
    auth.py
    backup.py
    config.py
    db.py
    errors.py
    logging_setup.py
    rate_limit.py
    repository.py
    serialization.py
    server.py
    validation.py
    routes/
      __init__.py
      health.py
      todos.py
  tests/
    conftest.py
    strategies.py
    test_auth.py
    test_backup.py
    test_config.py
    test_errors.py
    test_health.py
    test_properties.py
    test_rate_limit.py
    test_repository.py
    test_resilience.py
    test_serialization.py
    test_todos_api.py
    test_validation.py
  aidlc-docs/construction/todo-api/code/code-summary.md
```

논리 컴포넌트 대응: C-01 `config.py`, C-02 `app.py`, C-03 `auth.py`, C-04 `rate_limit.py`, C-05 `validation.py`, C-06 `repository.py`, C-07 `db.py`, C-08 `routes/todos.py`, C-09 `routes/health.py`, C-10 `errors.py`, C-11 `logging_setup.py`, C-12 `serialization.py`, C-13 `server.py`, C-14 `backup.py`, C-15 `.github/workflows/ci.yml`.

## 3. 실행 단계

### 단계 1. 프로젝트 구조 설정
- [x] `.gitignore` 작성 - `.venv/`, `instance/`, `logs/`, `backups/`, 파이썬 캐시, 테스트/Hypothesis 캐시 제외
- [x] `pyproject.toml` 작성 - 프로젝트 메타데이터, Python 3.12 요구, pytest 설정(`src` 경로, 테스트 경로)
- [x] `src/todo_api/__init__.py`, `src/todo_api/routes/__init__.py` 작성

### 단계 2. 설정과 오류 기반 (C-01, C-10)
- [x] `config.py` - 환경 변수 6개 읽기, 기본값, API 키 필수 및 32자 이상 검증, 위반 시 시작 거부 (SP-02)
- [x] `errors.py` - 업무 오류 클래스, 오류 코드, 공통 JSON 오류 형식, 전역 오류 처리기 등록 함수 (SP-06, BR-60~63)

### 단계 3. 로깅 (C-11)
- [x] `logging_setup.py` - JSON 포매터, 표준 출력과 순환 파일(5MB, 5개) 처리기, 요청 ID 생성과 전파, 요청 로그, 공통 응답 헤더, 로그 파일 권한 (OP-01~03, SP-07)

### 단계 4. 업무 로직: 검증과 직렬화 (C-05, C-12)
- [x] `validation.py` - 엔드포인트별 스키마 선언, 본문/쿼리 검증 함수, 제목 정규화, 모든 문제를 `details`로 수집 (SP-03, BR-01~05, BR-10~15)
- [x] `serialization.py` - 저장소 행과 Todo 표현 간 변환 (TP-03)

### 단계 5. 저장소 계층 (C-07, C-06)
- [x] `db.py` - 요청 단위 연결, busy timeout 5초, WAL, 멱등 스키마/인덱스 초기화, 잠금 시 1회 재시도, DB 파일과 디렉터리 권한 (RP-01, 02, 03, 06, SP-07)
- [x] `repository.py` - 생성, 목록 조회(필터, 최신 순), 단건 조회, 완료 상태 변경, 논리 삭제. 파라미터 바인딩만 사용, 유일 제약 위반을 `duplicate_title`로 변환 (SP-04, RP-04, BR-06~08, BR-20~43)

스키마는 `db.py`의 멱등 초기화로 만든다. 현재 범위에는 스키마 변경이 없어 별도 마이그레이션 스크립트는 만들지 않는다.

### 단계 6. 인증과 요청 제한 (C-03, C-04)
- [x] `auth.py` - `X-API-Key` 상수 시간 검증, 401 응답, `auth_failed` 이벤트 (SP-01)
- [x] `rate_limit.py` - Flask-Limiter 구성: IP당 분당 60회, 401 응답만 차감하는 분당 10회, 원격 주소만 사용, 429와 `Retry-After`, `rate_limited` 이벤트, 설정으로 한도 조정/비활성 (SP-05, TP-02)

### 단계 7. API 계층 (C-08, C-09, C-02, C-13)
- [x] `routes/todos.py` - 보호 엔드포인트 5개, 라우트 묶음 전체에 인증 적용, 변경 이벤트 기록 (FR-01~05, OP-03)
- [x] `routes/health.py` - 공개 상태 확인 엔드포인트, DB 읽기 확인 (FR-06, RP-05)
- [x] `app.py` - 앱 팩토리: 설정 인자 수용, 본문 크기 상한 16KB, 컴포넌트 조립 (TP-01)
- [x] `server.py` - 설정을 읽어 Waitress로 실행하는 진입점 (SP-07)

### 단계 8. 백업/복원 도구 (C-14)
- [x] `backup.py` - 온라인 백업, 무결성 검사, 최근 7개 보관, 검증된 복원(안전 사본, 보조 파일 정리), 명령줄 진입점 (RP-07)

### 단계 9. 테스트
- [x] `tests/conftest.py` - 임시 DB와 테스트용 키로 앱을 만드는 픽스처, 인증 헤더 도우미
- [x] `tests/strategies.py` - 유효/무효 제목 등 재사용 가능한 Hypothesis 제너레이터 (PBT-07)
- [x] 업무 로직 단위 테스트 - `test_validation.py`, `test_serialization.py`, `test_config.py`
- [x] 저장소 계층 단위 테스트 - `test_repository.py`
- [x] API 계층 테스트 - `test_todos_api.py`, `test_auth.py`, `test_rate_limit.py`, `test_errors.py`, `test_health.py` (엔드포인트별 정상/오류 케이스)
- [x] 속성 기반 테스트 - `test_properties.py`: P-01~P-07 필수, P-08(멱등성)과 P-09(상태 기반 모델) 권고 항목도 포함 (PBT-02, 03, 08)
- [x] 복원력 테스트 - `test_resilience.py`(RT-01~04, RT-08), `test_backup.py`(RT-05~07)

### 단계 10. 의존성 고정
- [x] 프로젝트 루트에 `.venv` 가상 환경 구성. `python3.12-venv`가 설치되어 있으면 표준 방식으로 만들고, 없으면 pip 없이 가상 환경을 만든 뒤 PyPA 공식 `get-pip.py`로 가상 환경 안에만 pip를 설치한다 (시스템에는 아무것도 설치하지 않음)
- [x] Flask, Flask-Limiter, Waitress 설치 후 실제 설치된 버전(하위 의존성 포함)을 `requirements.txt`에 `==`로 기록
- [x] pytest, Hypothesis, pip-audit 설치 후 `requirements-dev.txt`에 `==`로 기록 (`requirements.txt` 포함)
- [x] 생성한 코드가 가져오기(import)되고 테스트가 수집되는지 확인하는 스모크 검사 실행. 전체 테스트 실행과 결과 보고는 Build and Test 단계에서 수행

### 단계 11. 배포/운영 산출물
- [x] `.github/workflows/ci.yml` - 푸시와 풀 리퀘스트에서 Python 3.12로 의존성 설치, pytest(Hypothesis 시드 출력 포함), pip-audit 실행. 액션은 조회한 커밋 SHA로 고정 (SP-08, PBT-08)
- [x] `docs/coe-template.md` - 사후 분석 양식 (INC-02)
- [x] `docs/resilience-drill-log.md` - 복원 훈련 기록 양식 (RESILIENCY-14)

컨테이너 이미지나 배포 스크립트는 만들지 않는다 (로컬 전용, 자동 배포 없음).

### 단계 12. 문서
- [x] `README.md` (한국어) - 개요, 설치, 환경 변수와 API 키 생성 방법, 실행, API 사용 예시(curl), 오류 형식, 테스트와 취약점 스캔, 백업/복원, 문제 해결 절차, 롤백 절차, 복원 훈련 절차, 보안 유의 사항(디스크 암호화 전제, 바인딩 주소, HTML 이스케이프는 클라이언트 책임)
- [x] `aidlc-docs/construction/todo-api/code/code-summary.md` - 생성 파일 목록, 컴포넌트 대응, 요구사항 추적, 확장 규칙 준수 요약

### 단계 13. 마무리 점검
- [x] 계획의 파일 구조와 실제 생성 파일 대조
- [x] 확장 규칙 준수 점검 (Security, Resiliency, PBT 부분 적용)
- [x] 1장의 요구사항 추적 체크박스 갱신
- [x] `aidlc-state.md` 갱신, 완료 메시지 제시 및 승인 요청

## 4. 범위와 규모
- 총 13단계, 생성 파일 약 40개 (애플리케이션 17, 테스트 14, 설정/문서/CI 9, 요약 문서 1)
- git 커밋은 수행하지 않는다 (요청 시에만 수행)
