# Code Generation 계획 - 서버 종료용 실행 파일 (3차 워크플로)

이 문서는 3차 워크플로 Code Generation의 단일 기준 문서다.

## 1. 컨텍스트

| 항목 | 내용 |
|---|---|
| 유닛 | `web-ui`의 실행 파일 부분에 대한 추가 |
| 프로젝트 유형 | Brownfield |
| 기준 문서 | `aidlc-docs/inception/requirements/stop-server-requirements.md` |
| 따르는 기존 패턴 | 2차 NFR 설계의 WTP-04(순수 계산, 환경 확인, 부수 효과 분리), WSP-06(키를 다루지 않음) |

### 요구사항 추적
- [x] SFR-01 종료용 실행 파일 - 단계 1, 3
- [x] SFR-02 종료 대상 - 단계 1, 2
- [x] SFR-03 결과 안내 - 단계 1, 2

## 2. 파일 변경 목록

| 파일 | 구분 | 변경 |
|---|---|---|
| `src/todo_api/launcher.py` | 수정 | 프로세스 정보 모델, 대상 선택(순수 함수), 프로세스 목록 읽기, 종료 실행, `stop` 명령. 시작 파일로 띄운 서버가 밖에서 종료됐을 때의 안내 한 줄 |
| `todo-stop.bat` | 신규 | 실행 로직의 `stop` 명령 호출 (다른 두 배치 파일과 같은 구조) |
| `tests/test_launcher.py` | 수정 | 대상 선택 예제, 종료 흐름(가짜 부수 효과), 실제 서버 프로세스를 띄워 끄는 테스트 |
| `tests/test_launcher_properties.py` | 수정 | 대상 선택의 불변 조건 속성 |
| `tests/strategies.py` | 수정 | 프로세스 목록 제너레이터 |
| `README.md` | 수정 | 실행 파일 표와 사용법, 문제 해결의 종료 방법 |
| `aidlc-docs/construction/build-and-test/e2e-test-instructions.md` | 수정 | 수동 확인 항목 추가 |
| `aidlc-docs/construction/build-and-test/unit-test-instructions.md` | 수정 | 테스트 수 갱신 |
| `aidlc-docs/inception/reverse-engineering/code-structure.md` | 수정 | 추가된 파일과 명령 반영 |
| `aidlc-docs/construction/stop-server/code/code-summary.md` | 신규 | 코드 생성 요약 |
| `aidlc-docs/construction/build-and-test/stop-server-build-and-test-summary.md` | 신규 | 빌드 및 테스트 요약 (Build and Test 단계) |

프로젝트 밖: Windows 바탕화면에 "To-Do 종료" 바로 가기 1개.

## 3. 실행 단계

### 단계 1. 실행 로직
- [x] `launcher.py`에 프로세스 정보 모델과 대상 판정 함수 추가 - 현재 사용자의 프로세스이고, 실행 인자에 `-m todo_api.server`가 연속된 두 인자로 있고, 작업 폴더가 프로젝트 폴더와 같을 때만 대상 (SNFR-02)
- [x] 프로세스 목록 읽기, 정상 종료 요청 후 최대 5초 대기, 남으면 강제 종료, 실제로 끝났는지 확인 (SNFR-03, 04)
- [x] `stop` 명령과 결과 안내 (SFR-03). API 키를 읽지 않는다 (SNFR-01)

### 단계 2. 테스트
- [x] `tests/strategies.py`에 프로세스 목록 제너레이터 추가
- [x] `tests/test_launcher_properties.py`에 대상 선택 속성 추가 - 선택된 것은 모두 조건에 맞고, 조건에 맞는 것은 모두 선택된다 (SNFR-05)
- [x] `tests/test_launcher.py`에 예제 추가 - 비슷하지만 대상이 아닌 프로세스(다른 폴더, 다른 사용자, 인자 문자열 안에만 이름이 있는 셸, 실행 로직 자신), 종료 흐름 세 가지(껐음, 없음, 못 껐음), 실제 서버 프로세스 종료
- [x] 체크포인트: 전체 pytest 실행

### 단계 3. 배치 파일과 바로 가기
- [x] `todo-stop.bat` 작성 (CRLF)
- [x] 확인: Windows 명령 해석기로 실제 실행해 실행 중인 서버가 꺼지는지 확인
- [x] Windows 바탕화면에 "To-Do 종료" 바로 가기 생성 (같은 이름이 없을 때만)

### 단계 4. 문서
- [x] `README.md` 수정
- [x] 수동 확인 절차, 단위 테스트 지침, 리버스 엔지니어링 문서 갱신
- [x] `code-summary.md` 작성

### 단계 5. 마무리 점검
- [x] 전체 테스트, 취약점 스캔
- [x] 확장 규칙 준수 점검
- [x] `aidlc-state.md` 갱신

## 4. 범위
- 실제 서버 프로세스를 끄는 자동 테스트는 그 테스트가 직접 띄운 서버만 끈다. 사용자가 실행해 둔 서버를 건드리지 않는다
- 단계 3의 확인은 실제로 실행 중인 서버를 끈다. 확인 뒤 다시 띄워 둔다
- git 커밋과 푸시는 수행하지 않는다
