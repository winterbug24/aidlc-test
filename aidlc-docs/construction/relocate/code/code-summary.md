# 코드 요약: relocate (5차 워크플로, 프로젝트를 D 드라이브로 이전)

요구사항: `aidlc-docs/inception/requirements/relocate-requirements.md`
계획: `aidlc-docs/construction/plans/relocate-code-generation-plan.md`

## 코드 변경
| 파일 | 변경 | 요구사항 |
|---|---|---|
| `todo-start.bat`, `todo-stop.bat`, `todo-copy-key.bat` | `:locate`가 WSL 네트워크 경로(그 배포판)와 드라이브 경로(`D:\...` → `/mnt/d/...`, 기본 배포판)를 모두 인식. 먼저 같은 폴더에 `src\todo_api`가 있는지 확인하고 없으면 안내 후 종료. `wsl.exe -d %DISTRO%` → `wsl.exe %DISTRO_ARGS%` | RFR-01 |
| `README.md` | 프로젝트 위치 안내, 드라이브에 둘 때의 권한 보호(`icacls`), 속도, `core.filemode` | RNFR-03 |
| `tests/test_ui_display.py` | 넓은 창의 본문 최대 폭 기대값을 700px → 768px(48rem). 4차 변경 요청에서 폭을 넓힌 뒤 화면 테스트만 실행해 놓쳤던 기대값 | - |

커밋: `c9cd136` (배치 파일과 README, 옛 위치에서 커밋해 git 기록과 함께 옮김). 테스트 수정과 문서는 미커밋.

## 생성 중 고친 문제
- 배치 파일을 고치는 스크립트가 `:locate` 대신 `call :locate` 줄에서 잘라 본문이 사라졌다. 실행해 보니 "The system cannot find the batch label specified - locate"가 나와 발견했고, git에서 되돌린 뒤 다시 적용했다.
- 새 위치의 `python3`가 pyenv의 3.7.4로 잡혀 가상 환경이 잘못 만들어졌다. 지우고 `/usr/bin/python3.12`로 다시 만들었다. 이 시스템 파이썬에는 ensurepip가 없어 옛 가상 환경의 pip(`pip --python`)로 새 환경에 pip와 의존성을 설치했다. 설치 목록은 옛 환경과 같다(51개).

## 환경 작업
| 작업 | 결과 |
|---|---|
| 서버 정지와 백업 | 옛 위치 서버 종료, `backups/todo-20261014T075603242412Z.db` 생성 |
| 복사 | `rsync -rlt`로 `.venv`와 캐시를 뺀 전체 복사 (2.8MB). HEAD(`c9cd136`), 미커밋 변경, `.env` 해시, DB 내용 해시(13행)가 옛 위치와 같음. `git fsck` 이상 없음 |
| git | 새 저장소에 `core.filemode=false` |
| Windows 권한 | `.env`, `instance`, `backups`, `logs`: 상속 끊고 현재 사용자와 SYSTEM만 모든 권한. 폴더 안의 파일은 이 권한을 물려받음. WSL에서 읽기/쓰기 확인 |
| 가상 환경 | Python 3.12.3, `requirements-dev.txt` 설치, `pip check` 이상 없음 |
| 바탕화면 바로 가기 | `To-Do 시작`, `To-Do 종료`, `To-Do 키 복사` → `D:\workspace\to_do\todo-*.bat`, 작업 폴더 `D:\workspace\to_do` |
