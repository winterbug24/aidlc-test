# Code Generation 계획 - web-ui

이 문서는 2차 워크플로 Code Generation의 단일 기준 문서다. 생성 단계에서는 여기에 적힌 단계만, 적힌 순서대로 수행한다.

## 1. 유닛 컨텍스트

| 항목 | 내용 |
|---|---|
| 유닛 | `web-ui` (화면, 화면 제공 라우트, Windows 실행 파일, 테스트) |
| 프로젝트 유형 | Brownfield (기존 구조 `src/todo_api/`, `tests/`를 그대로 사용) |
| 워크스페이스 루트 | `/home/winterbug/aidlc-test` |
| 의존하는 기존 요소 | 기존 API 6개 엔드포인트(계약 변경 없음), 앱 팩토리, 요청 훅, 서버 진입점 |
| 소유 데이터 | 없음 (DB 스키마 변경 없음). 브라우저 저장소의 키 한 항목과 프로젝트 루트의 키 파일 `.env`만 다룸 |
| 입력 문서 | 요구사항, 사용자 스토리, 기능 설계 4종, NFR 요구사항 2종, NFR 설계 2종, 리버스 엔지니어링의 `code-structure.md` |

### 스토리 추적

- [x] US-01 실행 파일로 서버와 화면 열기 - 단계 4, 5, 6
- [x] US-02 이미 실행 중일 때 화면만 열기 - 단계 4, 5
- [x] US-03 포트가 사용 중일 때 빈 포트로 열기 - 단계 4, 5
- [x] US-04 키를 다시 복사하기와 서버 끄기 - 단계 4, 5, 6
- [x] US-05 키를 입력해 들어가기 - 단계 2, 8
- [x] US-06 다음 방문 때 바로 들어가기 - 단계 2, 8
- [x] US-07 키 지우기 - 단계 2, 8
- [x] US-08 목록 보기 - 단계 2, 8
- [x] US-09 할 일 추가하기 - 단계 2, 8
- [x] US-10 완료 체크와 해제 - 단계 2, 8
- [x] US-11 삭제하기 - 단계 2, 8
- [x] US-12 필터로 골라 보기 - 단계 2, 8
- [x] US-13 새로고침 - 단계 2, 8
- [x] US-14 Windows에서 깔끔하게 보이기 - 단계 2, 8
- [x] US-15 잘못된 키와 바뀐 키 - 단계 2, 8
- [x] US-16 입력 오류 안내 - 단계 2, 8
- [x] US-17 요청 제한 안내 - 단계 2, 8
- [x] US-18 서버에 연결할 수 없을 때 - 단계 2, 8

## 2. 파일 변경 목록

### 새로 만드는 파일

| 파일 | 논리 컴포넌트 | 내용 |
|---|---|---|
| `src/todo_api/security_headers.py` | W-01 | 모든 응답에 보안 헤더와 캐시 헤더 설정 |
| `src/todo_api/routes/web.py` | W-02 | `/api_test`와 화면 파일 제공 (고정 목록, 공개) |
| `src/todo_api/web/index.html` | W-03 | 화면 문서 |
| `src/todo_api/web/app.css` | W-03 | 스타일 (밝은/어두운 테마) |
| `src/todo_api/web/app.js` | W-03a~e | 화면 스크립트 |
| `src/todo_api/launcher.py` | W-04, 05, 06 | 실행 로직 (순수 계산, 환경 확인, 부수 효과, 명령 진입점) |
| `todo-start.bat` | W-07 | Windows 시작용 배치 파일 |
| `todo-copy-key.bat` | W-07 | Windows 키 복사용 배치 파일 |
| `tests/test_security_headers.py` | W-08 | 모든 종류의 응답에 헤더가 붙는지 |
| `tests/test_web_routes.py` | W-08 | 화면 파일 제공, 콘텐츠 유형, 경로 탈출 차단, 공개 범위 |
| `tests/test_launcher.py` | W-11 | 실행 로직 예제 기반 테스트 |
| `tests/test_launcher_properties.py` | W-11 | 실행 로직 속성 기반 테스트 (WP-01~05) |
| `tests/test_ui_key.py` | W-10 | 브라우저 테스트: 키 입력, 저장, 지우기 (US-05~07, 15) |
| `tests/test_ui_todos.py` | W-10 | 브라우저 테스트: 목록, 추가, 체크, 삭제, 필터, 새로고침 (US-08~13) |
| `tests/test_ui_errors.py` | W-10 | 브라우저 테스트: 입력 오류, 요청 제한, 연결 실패 (US-16~18) |
| `tests/test_ui_display.py` | W-10 | 브라우저 테스트: 테마, 좁은 창, 키보드, 1,000건, 요청 수 (US-14) |
| `aidlc-docs/construction/web-ui/code/code-summary.md` | - | 코드 생성 요약 (문서) |

### 고치는 기존 파일 (제자리 수정, 사본을 만들지 않음)

| 파일 | 변경 |
|---|---|
| `src/todo_api/app.py` | 응답 헤더 컴포넌트와 화면 라우트 묶음 등록, Flask 기본 정적 파일 경로 끄기 |
| `src/todo_api/logging_setup.py` | `nosniff`, `no-store` 헤더 설정을 `security_headers.py`로 옮김. 요청 ID 헤더와 요청 로그는 유지 |
| `tests/conftest.py` | 브라우저 테스트 장치 추가 (실제 서버 기동, 콘솔 오류 감시, 키가 저장된 상태로 시작하는 도우미) |
| `tests/strategies.py` | 포트 상태 배치와 키 제너레이터 추가 |
| `requirements-dev.txt` | playwright, pytest-playwright와 하위 의존성을 `==`로 추가 |
| `pyproject.toml` | 브라우저 테스트 표식(marker) 등록 |
| `.gitignore` | 브라우저 테스트 산출물 디렉터리 제외 |
| `.github/workflows/ci.yml` | 브라우저 설치 단계, 실패 시 추적 자료 보관 단계 추가 |
| `README.md` | 화면, 실행 파일, 키 저장 위험, 브라우저 테스트, 문제 해결 보강 |
| `aidlc-docs/inception/reverse-engineering/` 중 4개 문서 | 화면 추가를 반영해 갱신 (아키텍처, 코드 구조, API 문서, 기술 스택, 메타데이터의 날짜) |

### 고치지 않는 파일
기존 API 모듈(`auth.py`, `rate_limit.py`, `validation.py`, `repository.py`, `db.py`, `errors.py`, `serialization.py`, `config.py`, `server.py`, `backup.py`, `routes/todos.py`, `routes/health.py`), 기존 테스트 파일 12개, `requirements.txt`.

## 3. 실행 단계

### 단계 1. 응답 헤더 컴포넌트 (서버 쪽 기반)
- [x] `security_headers.py` 작성 - 헤더 상수, 콘텐츠 보안 정책 조립, 앱 등록 함수 (WSP-01, WSEC-01~06)
- [x] `logging_setup.py` 수정 - 헤더 두 줄을 제거하고 나머지는 유지
- [x] `app.py` 수정 - 응답 헤더 컴포넌트 등록
- [x] 체크포인트: 기존 테스트 161개 실행, 모두 통과 확인

### 단계 2. 화면 라우트와 화면 파일
- [x] `web/index.html` 작성 - 영역 구조, 견본 항목, 확인 창, `data-testid`, 빈 아이콘 선언, 한국어 문서 선언 (프런트엔드 컴포넌트 설계)
- [x] `web/app.css` 작성 - CSS 변수 기반 밝은/어두운 테마, Windows 글꼴, 유연한 배치, 포커스 표시 (WDP-01~05)
- [x] `web/app.js` 작성 - KeyStore, ApiClient, AppState, 화면 갱신, 동작 처리 (WSP-04, 05, WRP-01~03, WPP-02~04)
- [x] `routes/web.py` 작성 - 고정 목록 기반 제공, 공개 묶음 명시 (WSP-02, 03)
- [x] `app.py` 수정 - 화면 라우트 묶음 등록, 기본 정적 파일 경로 끄기

### 단계 3. 서버 쪽 테스트
- [x] `tests/test_security_headers.py` - 화면, API 성공, 401, 404, 429, 500 응답 모두에 다섯 헤더와 캐시 헤더. 정책에 인라인 허용이 없는지
- [x] `tests/test_web_routes.py` - 세 파일의 200과 콘텐츠 유형, 끝의 `/` 유무, 목록에 없는 이름과 경로 탈출 시도의 404, 인증 없이 화면이 열리고 `/todos`는 계속 401, 화면 파일에 키와 할 일 데이터가 없는지, 파일 크기 합계 60KB 이내
- [x] 체크포인트: 전체 pytest 실행

### 단계 4. 실행 로직
- [x] `launcher.py` 작성
  - 순수 계산: 포트 선택, 키 파일 쓰기/읽기 형식, 키 생성 (WTP-04)
  - 환경 확인: 우리 서버 식별(WSL 안에서만), WSL 쪽 포트 확인, Windows 수신 포트 목록 해석, 서버 응답 대기 (WRP-04, 05, WSP-07)
  - 부수 효과: 서버 프로세스 시작과 정리, 클립보드 복사, 브라우저 열기, 안내 출력 (WSP-06)
  - 명령 진입점: `start`, `copy-key`

### 단계 5. 실행 로직 테스트
- [x] `tests/strategies.py` 수정 - 포트 상태 배치, 유효한 키 제너레이터 (PBT-07)
- [x] `tests/test_launcher_properties.py` - WP-01~05 (PBT-02, 03)
- [x] `tests/test_launcher.py` - 키 파일 생성과 권한, 기존 키 파일 보존, Windows 수신 포트 목록 해석, 실제 테스트 서버로 우리 서버 식별, 다른 프로그램이 쓰는 포트 판정, 서버 응답 대기의 성공과 시간 초과, 시작 흐름(재사용, 새로 시작, 빈 포트 없음)을 가짜 부수 효과로 검증, 출력에 키가 없는지

### 단계 6. Windows 배치 파일
- [x] `todo-start.bat` 작성 - 자기 위치에서 배포판과 경로 추출, 실행 로직의 `start` 호출, 끝나면 창 유지 (WR-80)
- [x] `todo-copy-key.bat` 작성 - 실행 로직의 `copy-key` 호출
- [x] 확인: 이 PC의 Windows 명령 해석기로 두 파일을 실제 실행해 경로 추출과 호출이 되는지 확인 (더블클릭과 창 닫기는 Build and Test의 수동 확인)

### 단계 7. 브라우저 테스트 의존성
- [x] `.venv`에 playwright, pytest-playwright 설치 후 실제 설치된 버전(하위 의존성 포함)을 `requirements-dev.txt`에 `==`로 추가
- [x] Chromium 설치 (`python -m playwright install chromium`, 사용자 홈의 캐시 디렉터리에 내려받음)
- [x] `pyproject.toml` 수정 - 브라우저 테스트 표식 등록
- [x] `.gitignore` 수정 - 브라우저 테스트 산출물 제외
- [x] 취약점 스캔 실행 (`pip-audit`)

### 단계 8. 브라우저 테스트
- [x] `tests/conftest.py` 수정 - 임의의 빈 포트에 실제 앱을 띄우는 장치, 콘솔 오류와 정책 위반 감시, 준비 데이터 도우미, 키가 저장된 상태로 화면을 여는 도우미 (WTP-01, 02)
- [x] `tests/test_ui_key.py` - US-05, 06, 07, 15
- [x] `tests/test_ui_todos.py` - US-08, 09, 10, 11, 12, 13
- [x] `tests/test_ui_errors.py` - US-16, 17, 18 (요청 가로채기로 실패 상황 구성, WTP-03)
- [x] `tests/test_ui_display.py` - US-14 (어두운 테마, 480px, 키보드 흐름), 1,000건 목록, 첫 화면 요청 수 4회, 가만히 둔 화면의 요청 0회, 주소와 콘솔에 키가 없는지
- [x] 체크포인트: 전체 pytest 실행 (기존 161개 + 새 테스트)

### 단계 9. CI
- [x] `.github/workflows/ci.yml` 수정 - 브라우저 설치 단계, 실패 시 추적 자료 보관 단계(새 액션은 커밋 SHA로 고정)

### 단계 10. 문서
- [x] `README.md` 수정 - 화면 사용법, 실행 파일과 바로 가기 만들기, 키 복사 파일, 키 저장 방식과 위험, 포트가 바뀌면 키를 다시 입력해야 하는 이유, 브라우저 테스트 실행법, 화면 관련 문제 해결, 프로젝트 구조 갱신
- [x] `aidlc-docs/construction/web-ui/code/code-summary.md` 작성 - 생성/수정 파일, 스토리 추적, 검증 결과, 색 조합과 대비 값 표(WDP-02), 설계와 달라진 점, 확장 규칙 준수 요약
- [x] 리버스 엔지니어링 문서 갱신 - `architecture.md`, `code-structure.md`, `api-documentation.md`, `technology-stack.md`, `reverse-engineering-timestamp.md`

### 단계 11. 마무리 점검
- [x] 파일 변경 목록과 실제 결과 대조. 사본 파일(`_new`, `_modified` 등)이 없는지 확인
- [x] 전체 테스트, 취약점 스캔, 의존성 일관성 확인
- [x] 실제 서버를 띄워 화면 파일과 헤더를 직접 확인
- [x] 확장 규칙 준수 점검 (Security, Resiliency, PBT 부분 적용)
- [x] 1장의 스토리 추적 체크박스 갱신
- [x] `aidlc-state.md` 갱신, 완료 메시지 제시 및 승인 요청

## 4. 범위와 규모
- 총 11단계. 새 파일 17개(애플리케이션 6, 배치 2, 테스트 8, 문서 1), 수정 파일 9개와 리버스 엔지니어링 문서 5개
- 실행 의존성(`requirements.txt`)은 바꾸지 않는다
- git 커밋과 푸시는 수행하지 않는다 (요청 시에만 수행)
- 서버를 띄우는 확인은 임시 포트와 임시 DB로 하고, 사용자의 실제 DB(`instance/todo.db`)와 키 파일(`.env`)은 건드리지 않는다. 단, 단계 6의 배치 파일 확인은 실제 키 파일을 읽는다(없으면 만든다)
