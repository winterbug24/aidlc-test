# 기술 스택

## 프로그래밍 언어
- Python - 3.12 - 애플리케이션, 테스트, 운영 도구 전체

## 프레임워크와 라이브러리
- Flask - 3.1.3 - 웹 프레임워크
- Flask-Limiter - 4.1.1 - 요청 제한 (메모리 저장소)
- Waitress - 3.0.2 - WSGI 서버
- sqlite3 - 표준 라이브러리 - 데이터 저장 (WAL 모드)
- logging - 표준 라이브러리 - JSON 구조화 로그 (자체 포매터)

프런트엔드는 빌드 도구 없는 HTML, CSS, JavaScript 각 한 파일이다 (2차 워크플로에서 추가). 프레임워크와 외부 라이브러리는 쓰지 않는다. Jinja2는 Flask의 하위 의존성으로 설치되어 있으나 쓰이지 않는다.

## 인프라
- 로컬 PC (WSL Ubuntu에서 검증) - 실행 환경
- SQLite 파일 - 데이터 저장
- GitHub Actions - CI

## 빌드 도구
- pip + venv - 의존성 설치와 격리
- `requirements.txt`, `requirements-dev.txt` - 전체 의존성 `==` 고정

## 테스트 도구
- pytest - 9.1.1 - 테스트 러너
- Hypothesis - 6.169.0 - 속성 기반 테스트
- pip-audit - 2.10.1 - 의존성 취약점 스캔

## 2차 워크플로(웹 화면)에서 추가된 것
- Playwright - 1.63.0 - 브라우저 자동화 테스트 (Chromium, 화면 없는 모드)
- pytest-playwright - 0.10.0 - pytest 연동
- Windows 배치 파일 2개 - 서버 시작과 키 복사 (WSL의 Python 실행 로직을 호출)
