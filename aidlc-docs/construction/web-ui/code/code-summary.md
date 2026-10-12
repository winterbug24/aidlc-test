# 코드 생성 요약 - web-ui

계획 문서: `aidlc-docs/construction/plans/web-ui-code-generation-plan.md` (11단계 모두 완료)

## 1. 새로 만든 파일

### 애플리케이션

| 파일 | 논리 컴포넌트 | 내용 |
|---|---|---|
| `src/todo_api/security_headers.py` | W-01 | 모든 응답에 보안 헤더 5종과 캐시 헤더 설정 |
| `src/todo_api/routes/web.py` | W-02 | `/api_test`와 화면 파일 두 개를 고정 목록으로 제공. 공개 묶음 |
| `src/todo_api/web/index.html` | W-03 | 화면 문서 (4.9KB) |
| `src/todo_api/web/app.css` | W-03 | 스타일, 밝은/어두운 테마 (5.4KB) |
| `src/todo_api/web/app.js` | W-03a~e | 화면 스크립트: KeyStore, ApiClient, 상태, 화면 갱신, 동작 처리 (17.1KB) |
| `src/todo_api/launcher.py` | W-04, 05, 06 | 실행 로직: 포트 선택, 키 파일, 포트 상태 판정, 서버 시작과 정리 |
| `todo-start.bat` | W-07 | Windows 시작용 배치 파일 |
| `todo-copy-key.bat` | W-07 | Windows 키 복사용 배치 파일 |

화면 파일 세 개의 합계는 27.3KB다 (기준 60KB 이내).

### 테스트

| 파일 | 테스트 수 | 종류 | 대상 |
|---|---|---|---|
| `tests/test_security_headers.py` | 13 | 예제 기반 | 화면, API, 401, 404, 405, 409, 429, 500 응답의 헤더와 정책 내용 |
| `tests/test_web_routes.py` | 27 | 예제 기반 | 화면 파일 제공, 콘텐츠 유형, 경로 탈출 차단, 공개 범위, 인라인 코드 없음, 파일 크기 |
| `tests/test_launcher.py` | 31 | 예제 기반 | 키 파일, 포트 판정(실제 소켓과 실제 앱), 시작 흐름, 키 복사, 실제 서버 프로세스 |
| `tests/test_launcher_properties.py` | 6 | 속성 기반 | WP-01~05 |
| `tests/test_ui_key.py` | 13 | 브라우저 | US-05, 06, 07, 15, 17 |
| `tests/test_ui_todos.py` | 22 | 브라우저 | US-08~13 |
| `tests/test_ui_errors.py` | 12 | 브라우저 | US-16, 17, 18 |
| `tests/test_ui_display.py` | 13 | 브라우저 | US-14, 요청 수, 1,000건 목록 |
| **새 테스트 합계** | **137** | | |

## 2. 고친 기존 파일

| 파일 | 변경 |
|---|---|
| `src/todo_api/app.py` | 응답 헤더 컴포넌트와 화면 라우트 묶음 등록, Flask 기본 정적 파일 경로 끔 |
| `src/todo_api/logging_setup.py` | `nosniff`, `no-store` 헤더 설정 두 줄을 `security_headers.py`로 옮김 |
| `tests/conftest.py` | 실제 서버 기동 장치, 화면 조작 도우미, 콘솔 오류 감시 추가 |
| `tests/strategies.py` | 포트 상태 배치와 키 제너레이터 추가 |
| `requirements-dev.txt` | playwright 1.63.0, pytest-playwright 0.10.0과 하위 의존성 4개 추가 (모두 `==`) |
| `pyproject.toml` | `e2e` 표식 등록 |
| `.gitignore` | `test-results/` 제외 |
| `.github/workflows/ci.yml` | 브라우저 설치 단계, 실패 시 추적 자료 보관 단계 추가 |
| `README.md` | "웹 화면" 절 추가, 테스트/문제 해결/보안 유의 사항/프로젝트 구조 보강 |

고치지 않은 파일: 기존 API 모듈 12개, 기존 테스트 파일 12개, `requirements.txt`. 사본 파일은 만들지 않았다.

## 3. 스토리 추적

| 스토리 | 구현 | 검증 |
|---|---|---|
| US-01 실행 파일로 서버와 화면 열기 | `launcher.py` `run_start`, `todo-start.bat` | `test_launcher.py`, 배치 파일 실제 실행 |
| US-02 이미 실행 중일 때 화면만 열기 | `launcher.py` `choose_port`, `is_our_server` | `test_launcher.py`, WP-01 |
| US-03 포트가 사용 중일 때 빈 포트로 열기 | `launcher.py` `probe_ports`, `choose_port` | `test_launcher.py`, WP-02, WP-03 |
| US-04 키 다시 복사하기와 서버 끄기 | `launcher.py` `run_copy_key`, `stop_server`, `todo-copy-key.bat` | `test_launcher.py`, 배치 파일 실제 실행 |
| US-05 키를 입력해 들어가기 | `app.js` `submitKey` | `test_ui_key.py` |
| US-06 다음 방문 때 바로 들어가기 | `app.js` `start`, KeyStore | `test_ui_key.py` |
| US-07 키 지우기 | `app.js` `clearKey` | `test_ui_key.py` |
| US-08 목록 보기 | `app.js` `renderList`, `fillItem` | `test_ui_todos.py` |
| US-09 할 일 추가하기 | `app.js` `addTodo` | `test_ui_todos.py` |
| US-10 완료 체크와 해제 | `app.js` `toggleTodo` | `test_ui_todos.py` |
| US-11 삭제하기 | `app.js` `askDelete`, `confirmDelete`, `<dialog>` | `test_ui_todos.py` |
| US-12 필터로 골라 보기 | `app.js` `changeFilter` | `test_ui_todos.py` |
| US-13 새로고침 | `app.js` `reloadTodos` | `test_ui_todos.py`, `test_ui_display.py` |
| US-14 Windows에서 깔끔하게 보이기 | `app.css`, `index.html` | `test_ui_display.py`, 수동 확인 필요 항목 있음 |
| US-15 잘못된 키와 바뀐 키 | `app.js` `handleFailure` | `test_ui_key.py` |
| US-16 입력 오류 안내 | `app.js` `handleFailure`, `showNotice` | `test_ui_errors.py` |
| US-17 요청 제한 안내 | `app.js` `describeRejection` | `test_ui_errors.py`, `test_ui_key.py` (실제 인증 실패 한도 포함) |
| US-18 서버에 연결할 수 없을 때 | `app.js` `callApi`, `handleFailure` | `test_ui_errors.py` |

## 4. 검증 결과 (코드 생성 중 실행)

| 항목 | 결과 |
|---|---|
| 전체 테스트 (`pytest`) | 298개 통과 (기존 161개 + 새 137개), 약 58초. 시드를 바꿔 두 번 실행해 모두 통과 |
| 기존 테스트 161개 | 수정 없이 통과 (헤더 변경 직후와 마지막에 각각 확인) |
| 의존성 취약점 스캔 | 알려진 취약점 없음 |
| 의존성 일관성 (`pip check`) | 문제 없음 |
| 실제 서버(Waitress) | 화면 문서에 보안 헤더 5종과 `no-store` 확인, 화면 파일 200, 목록 밖 경로 404, `/todos` 401 |
| `todo-copy-key.bat` | Windows 명령 해석기로 실행. 한글 안내 출력, 클립보드 내용이 키와 일치, 창에 키 미표시 |
| `todo-start.bat` | Windows 명령 해석기로 실행. WSL에서 서버가 떴고 WSL과 Windows 양쪽에서 화면 200. 서버 프로세스의 명령줄에 키 없음 |
| 실행 로직 강제 종료 | 실행 로직을 강제로 죽이면 서버 프로세스도 함께 끝남 |
| 화면 모습 | 밝은 테마, 어두운 테마, 480px 창을 화면 갈무리로 확인. 배치와 색은 의도대로. 한글 글자 모양은 확인하지 못함 (아래 참고) |

### 확인하지 못한 것
- **더블클릭과 창 닫기**: 배치 파일은 명령 해석기로 실행해 확인했다. 탐색기에서 더블클릭하는 동작, 바로 가기로 실행하는 동작, 실행 창을 닫았을 때 서버가 끝나는지는 직접 확인하지 못했다.
- **브라우저가 실제로 열리는지**: 실행 로직이 브라우저 열기 명령을 호출하고 성공 코드를 받은 것까지 확인했다. 창이 실제로 떴는지는 볼 수 없었다.
- **한글 글자 모양**: 화면 갈무리는 WSL 안의 Chromium으로 찍었는데 WSL에 한글 글꼴이 없어 한글이 빈 상자로 나왔다. Windows의 브라우저에는 맑은 고딕이 있어 문제가 없을 것으로 보지만 직접 보지는 못했다.
- **실제 Edge와 Chrome**: 자동 테스트는 Playwright의 Chromium 하나로만 돌렸다.
- **화면 배율 125%, 150%와 Windows 설정을 실제로 바꿨을 때의 테마 전환**
- **GitHub Actions**: 워크플로를 고쳤지만 푸시하지 않아 실행되지 않았다. 브라우저 설치 단계와 새 액션(`upload-artifact`)은 첫 푸시 때 확인이 필요하다.

위 항목은 Build and Test 단계의 수동 확인 절차로 넘긴다.

### 확인 과정에서 생긴 부수 효과
- 배치 파일을 실제로 실행하면서 Windows 클립보드에 API 키가 복사됐다. 확인 뒤 클립보드를 빈 값으로 바꿨다. 그 전에 클립보드에 있던 내용은 사라졌다.
- `todo-start.bat` 실행으로 기본 브라우저에 화면 탭이 하나 열렸을 수 있다.
- 서버를 잠깐 띄우면서 실제 DB(`instance/todo.db`)와 로그(`logs/`)가 사용됐다. 데이터를 바꾸는 요청은 보내지 않았다.

## 5. 색 조합과 대비 (WDP-02)

WCAG 대비 공식으로 계산한 값이다. 기준은 글자 4.5:1 이상, 테두리와 포커스 표시 3:1 이상이다.

| 용도 | 밝은 테마 | 대비 | 어두운 테마 | 대비 |
|---|---|---|---|---|
| 본문 글자 / 배경 | `#1b1b1b` / `#ffffff` | 17.22 | `#f2f2f2` / `#202020` | 14.55 |
| 흐린 글자(완료 항목, 안내) / 배경 | `#5c5c5c` / `#ffffff` | 6.69 | `#b4b4b4` / `#202020` | 7.86 |
| 흐린 글자 / 카드 배경 | `#5c5c5c` / `#f3f3f3` | 6.03 | `#b4b4b4` / `#2c2c2c` | 6.74 |
| 테두리 / 배경 | `#767676` / `#ffffff` | 4.54 | `#8c8c8c` / `#202020` | 4.85 |
| 포커스 표시 / 배경 | `#005fb8` / `#ffffff` | 6.31 | `#60cdff` / `#202020` | 9.06 |
| 주 버튼 글자 / 버튼 | `#ffffff` / `#005fb8` | 6.31 | `#00263a` / `#60cdff` | 8.72 |
| 삭제 글자 / 배경 | `#b3261e` / `#ffffff` | 6.54 | `#ffb4ab` / `#202020` | 9.60 |
| 삭제 버튼 글자 / 버튼 | `#ffffff` / `#b3261e` | 6.54 | `#4a0d09` / `#ffb4ab` | 9.14 |
| 오류 안내 글자 / 배경 | `#7a1410` / `#fdecea` | 9.49 | `#ffdad6` / `#4a1512` | 11.55 |
| 정보 안내 글자 / 배경 | `#0b3d91` / `#e8f0fe` | 8.77 | `#d6e7ff` / `#0f2f52` | 10.80 |

## 6. 설계와 달라진 점

| 항목 | 내용 | 이유 |
|---|---|---|
| 키 입력 칸의 종류 | 비밀번호 칸이 아니라 일반 칸을 글자 가림 스타일로 표시 | 비밀번호 칸이면 브라우저가 저장을 제안한다(WR-16). 가림 스타일은 Chromium 계열에서만 동작하므로 Firefox에서는 키가 보인다. 기준 브라우저(Edge, Chrome)에서는 문제없다 |
| 필터 변경 실패 시 | 불러오지 못하면 필터 표시를 이전 값으로 되돌림 | 화면의 목록과 필터 표시가 어긋나지 않게 하기 위해 (UI-INV-03). 기능 설계에는 명시하지 않았던 경우 |
| 처리 중인 항목 | 버튼을 비활성화하지 않고 입력만 무시 | 비활성화하면 키보드 포커스가 사라진다 |
| 배치 파일의 배포판 인자 | `wsl.exe -d` 뒤의 배포판 이름에 따옴표를 붙이지 않음 | 따옴표를 붙이면 배포판을 찾지 못하는 것을 이 PC에서 확인. 이름에 공백이 있는 배포판은 지원하지 않는다 |
| 실행 로직과 Flask | 실행 로직을 `todo_api` 패키지 안에 두어, 실행할 때 패키지 초기화 과정에서 Flask가 함께 로드됨 | 설계는 "Flask를 가져오지 않는다"였다. 실행 로직의 코드는 Flask를 쓰지 않고 서버는 별도 프로세스로 띄우지만, 패키지 구조상 로드 자체는 일어난다. 동작에는 영향이 없다 |
| 서버 로그 출력 | 실행 파일로 띄운 서버의 요청 로그는 창에 내보내지 않음 | 요청 로그가 안내 문구를 밀어내지 않게. 로그는 로그 파일에 그대로 남는다 |
| 브라우저 테스트의 콘솔 감시 | 4xx/5xx 응답 때 브라우저가 남기는 "Failed to load resource" 기록은 제외 | 오류 상황을 일부러 만드는 테스트에서 항상 나오는 기록이다. 정책 위반과 스크립트 오류는 그대로 잡는다 |

## 7. 확장 규칙 준수 요약 (Code Generation 단계)

### Security Baseline
| 규칙 | 상태 | 근거 |
|---|---|---|
| SECURITY-01 | 준수 | 새 데이터 저장소 없음. 실행 파일이 만드는 키 파일은 600 권한 (`test_launcher.py`에서 검증). OS 디스크 암호화 전제는 1차와 같음 |
| SECURITY-02 | N/A | 네트워크 중개 장치 없음 |
| SECURITY-03 | 준수 | 화면 파일 요청도 기존 요청 로그에 남음. 화면 스크립트에 콘솔 출력 없음, 주소와 화면 글자에 키 없음 (테스트로 검증) |
| SECURITY-04 | 준수 | 다섯 헤더가 화면, API, 오류 응답 모두에 붙음 (`test_security_headers.py`). 정책에 `unsafe-inline`, `unsafe-eval` 없음. HSTS `max-age` 31536000. 화면 문서에 인라인 스크립트/스타일/이벤트 처리기 없음. 브라우저 테스트에서 정책 위반 0건 |
| SECURITY-05 | 준수 | 화면 파일은 고정 목록만 제공, 경로 탈출 시도 404. 화면은 서버 문자열을 텍스트로만 삽입 (`innerHTML` 등 미사용을 테스트로 고정, 위험한 제목과 오류 문구로 브라우저 검증). 서버 쪽 검증은 변경 없음 |
| SECURITY-06 | N/A | IAM 없음 |
| SECURITY-07 | 준수 | 실행 파일은 서버를 127.0.0.1에만 바인딩 |
| SECURITY-08 | 준수 | 화면 묶음만 공개로 명시, `/todos`는 계속 401 (테스트로 고정). CORS 헤더 없음 |
| SECURITY-09 | 준수 | 기본 정적 파일 경로를 끄고 정해진 파일만 제공. 오류 응답은 기존 공통 형식 |
| SECURITY-10 | 준수 | 새 의존성 6개 모두 `==` 고정, pip-audit 통과, 새 액션 SHA 고정, 화면은 외부 라이브러리 0개. 테스트용 브라우저는 고정된 Playwright 버전이 정한 빌드 |
| SECURITY-11 | 준수 | 오용 시나리오 WMU-01~10의 대응을 구현하고 테스트. 화면 파일 요청도 요청 제한 대상 (429 테스트) |
| SECURITY-12 | 준수 | 키는 암호학적 난수로 생성, 명령줄 인자와 창 출력에 없음 (테스트와 실제 프로세스 확인). 하드코딩된 키 없음. 브라우저 평문 저장은 수용한 위험 |
| SECURITY-13 | 준수 | 외부 스크립트 없음 (SRI 대상 없음) |
| SECURITY-14 | N/A | 로컬 전용 (1차와 같음) |
| SECURITY-15 | 준수 | 화면의 모든 호출이 실패를 값으로 돌려받아 처리. 실행 로직은 실패와 종료 시 서버 프로세스를 정리 |

### Resiliency Baseline
| 규칙 | 상태 | 근거 |
|---|---|---|
| RESILIENCY-01, 02, 03, 11, 12, 13 | 준수 | 1차 결정 유지, 변경 없음 |
| RESILIENCY-04 | 준수 | CI 워크플로에 화면 테스트 추가. 롤백과 배포 방식은 1차와 같음 |
| RESILIENCY-05 | 준수 | 기존 구조화 로그 사용 |
| RESILIENCY-06 | 준수 | 실행 로직이 `/health` 응답을 확인한 뒤 브라우저를 엶 |
| RESILIENCY-07, 08, 09 | N/A | 로컬 전용 |
| RESILIENCY-10 | 준수 | 화면 호출 제한 시간 15초, 포트 확인 제한 시간 1초, 실패 시 화면 상태 보존 |
| RESILIENCY-14 | 준수 | 화면의 실패 처리(연결 끊김, 시간 초과, 503, 429)와 실행 로직의 실패 경로를 자동 테스트. 수동 확인 항목은 Build and Test로 넘김 |
| RESILIENCY-15 | 준수 | README 문제 해결 절차에 화면과 실행 파일 관련 증상 9건 추가 |

### Property-Based Testing (부분 적용)
| 규칙 | 상태 | 근거 |
|---|---|---|
| PBT-02 | 준수 | WP-04 (키 파일 왕복) |
| PBT-03 | 준수 | WP-01, 02, 03, 05 (포트 선택과 키 생성의 불변 조건) |
| PBT-07 | 준수 | `tests/strategies.py`에 포트 상태 배치와 키 제너레이터 추가 |
| PBT-08 | 준수 | 축소 유지, CI에서 시드 로그 출력 (1차 구성 유지) |
| PBT-09 | 준수 | Hypothesis 유지. JavaScript는 대상 로직이 없어 프레임워크 미도입 |
