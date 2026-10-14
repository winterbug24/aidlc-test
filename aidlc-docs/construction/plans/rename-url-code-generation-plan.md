# 코드 생성 계획: rename-url (6차 워크플로, 화면 주소 변경)

요구사항: `aidlc-docs/inception/requirements/rename-url-requirements.md`. 실행 계획: 작은 변경이라 별도 파일 없이 이 문서에 기록한다. 실행 단계는 Code Generation, Build and Test이고 나머지 조건부 단계는 건너뛴다(새 컴포넌트, 데이터, NFR 변경 없음).

## 단계
- [x] Step 1: `src/todo_api/routes/web.py`의 `url_prefix`, `src/todo_api/launcher.py`의 `WEB_PATH`, `src/todo_api/web/index.html`의 파일 경로를 `/todo_list`로 (UFR-01, 02)
- [x] Step 2: 테스트의 기대 주소 변경: `conftest.py`, `test_web_routes.py`, `test_security_headers.py`, `test_launcher.py`, `test_ui_display.py`
- [x] Step 3: 현재 상태 문서 변경: README, 리버스 엔지니어링 문서 4개, `build-instructions.md`, `e2e-test-instructions.md`, `security-test-instructions.md`
- [x] Step 4: 관련 테스트 실행, 서버 재시작, 새 주소와 옛 주소 확인
