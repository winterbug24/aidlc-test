# 빌드 지침

파이썬 프로젝트라 컴파일 단계는 없다. "빌드"는 가상 환경을 만들고 고정된 의존성을 설치한 뒤 코드가 가져와지는지 확인하는 것이다.

## 사전 요건
- **도구**: Python 3.12, pip (표준 `venv`)
- **의존성**: `requirements.txt`(실행), `requirements-dev.txt`(개발/테스트, 화면 테스트용 Playwright 포함). 모두 `==`로 고정
- **환경 변수**: 빌드와 테스트에는 필요 없다. 서버 실행 시 `TODO_API_KEY`(32자 이상)가 필요하다
- **시스템**: Linux/WSL (검증 환경: WSL Ubuntu, Python 3.12.3). 디스크 약 600MB(화면 테스트용 Chromium 포함), PyPI와 Playwright 배포처 접속 필요

## 빌드 단계

모든 명령은 프로젝트 루트(`/home/winterbug/aidlc-test`)에서 실행한다.

### 1. 가상 환경 만들기
```bash
python3 -m venv .venv
```

`ensurepip` 오류로 실패하면 다음 중 하나를 선택한다.

```bash
# 방법 A (권장): 시스템 패키지 설치
sudo apt install python3.12-venv
python3 -m venv .venv

# 방법 B: 관리자 권한 없이, 가상 환경 안에만 pip 설치
python3 -m venv --without-pip .venv
curl -sSfo /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
.venv/bin/python /tmp/get-pip.py
```

현재 워크스페이스의 `.venv`는 방법 B로 만들어져 있다.

### 2. 의존성 설치
```bash
.venv/bin/python -m pip install -r requirements-dev.txt
```

실행만 할 때는 `requirements.txt`만 설치해도 된다.

### 3. 빌드 확인
```bash
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q src tests
```

### 4. 성공 기준
- `pip check`가 `No broken requirements found.`를 출력한다
- `compileall`이 오류 없이 끝난다
- **산출물**: 별도 패키지 파일은 만들지 않는다. `src/todo_api/`를 `PYTHONPATH=src`로 직접 실행한다
- **허용되는 경고**: 없음

### 5. 서버 실행 확인 (선택)
```bash
export TODO_API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
PYTHONPATH=src .venv/bin/python -m todo_api.server
# 다른 터미널에서
curl -s http://127.0.0.1:8000/health   # {"status":"ok"}
```

## 문제 해결

### `python3 -m venv`가 ensurepip 오류로 실패
- **원인**: Ubuntu는 `venv`의 pip 부분을 별도 패키지로 배포한다
- **해결**: 위 1단계의 방법 A 또는 B

### 의존성 설치 실패
- **원인**: PyPI에 접속할 수 없거나 Python 버전이 3.12가 아니다
- **해결**: `python3 --version`으로 버전을 확인하고 네트워크를 점검한다. 고정 버전은 Python 3.12에서 확인했다

### `ModuleNotFoundError: No module named 'todo_api'`
- **원인**: `PYTHONPATH=src` 없이 서버나 백업 도구를 실행했다
- **해결**: 명령 앞에 `PYTHONPATH=src`를 붙인다. pytest는 `pyproject.toml` 설정으로 자동 처리된다

### 서버가 `설정 오류`를 출력하고 종료
- **원인**: `TODO_API_KEY`가 없거나 32자 미만이다
- **해결**: 5단계처럼 키를 만들어 설정한다

## 화면 테스트용 브라우저 (2차 워크플로에서 추가)

화면(`/todo_list`)을 검증하는 브라우저 테스트를 돌리려면 의존성 설치 뒤에 브라우저를 한 번 내려받는다. 서버 실행만 할 때는 필요 없다.

### 1. Chromium 내려받기
```bash
.venv/bin/python -m playwright install chromium
```
- 사용자 홈의 `~/.cache/ms-playwright/`에 내려받는다 (약 115MB). 고정된 playwright 버전이 정한 빌드라 버전을 따로 고를 필요가 없다
- 이미 받았으면 바로 끝난다

### 2. 시스템 라이브러리 (Ubuntu/WSL)
브라우저가 `error while loading shared libraries`로 뜨지 않으면 다음을 실행한다. 관리자 권한이 필요하다.
```bash
sudo apt install -y libnss3 libnspr4 libasound2t64
```
이 PC에는 2026-10-12에 설치했다.

### 3. 확인
```bash
.venv/bin/python -m pytest -m e2e -q
```
- **기대 결과**: `60 passed`

### 문제 해결 추가

#### `BrowserType.launch: Executable doesn't exist`
- **원인**: Chromium을 내려받지 않았다
- **해결**: 위 1단계

#### `error while loading shared libraries: libnss3.so`
- **원인**: 시스템 라이브러리가 없다
- **해결**: 위 2단계

## Windows 실행 파일 (2차 워크플로에서 추가)
`todo-start.bat`, `todo-copy-key.bat`은 빌드할 것이 없다. 프로젝트 폴더에 `.venv`가 만들어져 있으면 바로 쓸 수 있다. 줄바꿈이 CRLF여야 하므로 편집기로 고칠 때 줄바꿈 형식을 바꾸지 않는다. 사용법은 `README.md`의 "웹 화면" 절, 확인 절차는 `e2e-test-instructions.md`에 있다.
