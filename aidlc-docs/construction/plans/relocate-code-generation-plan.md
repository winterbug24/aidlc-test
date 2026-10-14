# 코드 생성 계획: relocate (5차 워크플로, 프로젝트를 D 드라이브로 이전)

이 계획이 5차 워크플로 Code Generation의 유일한 기준이다. 요구사항: `aidlc-docs/inception/requirements/relocate-requirements.md`.

## 유닛 맥락
- **유닛**: `relocate`
- **옛 위치**: `/home/winterbug/aidlc-test` (`\\wsl.localhost\Ubuntu\home\winterbug\aidlc-test`)
- **새 위치**: `/mnt/d/workspace/to_do` (`D:\workspace\to_do`)
- **기준선**: 옛 위치에서 자동 테스트 343개 통과 (4차 워크플로)

## 단계

### Step 1: 배치 파일 수정 (옛 위치에서, RFR-01)
- [x] `todo-start.bat`, `todo-stop.bat`, `todo-copy-key.bat`의 `:locate`: WSL 네트워크 경로는 기존대로, 드라이브 경로는 `/mnt/<소문자 드라이브>/...`로 바꾸고 기본 배포판 사용. 두 경우 모두 같은 폴더에 `src\todo_api`가 없으면 안내 후 종료
- [x] README: 위치 안내와 D 드라이브 주의 사항(RNFR-03)
- [x] 변경을 커밋 (옛 위치의 git 기록에 포함시켜 함께 옮김)

### Step 2: 서버 정지와 백업 (RNFR-02)
- [x] 실행 중인 서버를 `launcher stop`으로 정지
- [x] 백업 도구로 DB 백업. 이전 전 DB 행 수와 `.env` 해시를 기록(키 값은 출력하지 않음)

### Step 3: 복사 (RFR-02)
- [x] `rsync`로 `.venv`와 캐시를 뺀 전체를 새 위치로 복사
- [x] 새 저장소에 `core.filemode=false` 설정. git 상태가 깨끗하고 HEAD가 같은지 확인
- [x] `.env` 해시, DB 행 수가 같은지 확인

### Step 4: Windows 권한 (RNFR-01)
- [x] `icacls`로 `.env`, `instance`, `backups`, `logs`의 상속을 끊고 현재 사용자와 SYSTEM에만 권한 부여
- [x] WSL에서 읽기/쓰기가 되는지 확인

### Step 5: 가상 환경
- [x] 새 위치에 `.venv` 생성, `requirements-dev.txt` 설치

### Step 6: 바탕화면 바로 가기 (RFR-03)
- [x] `To-Do 시작`, `To-Do 종료`, `To-Do 키 복사`를 새 경로로 다시 만듦

### Step 7: 문서
- [x] `aidlc-state.md`의 작업 공간 경로, 코드 요약(`aidlc-docs/construction/relocate/code/code-summary.md`)
