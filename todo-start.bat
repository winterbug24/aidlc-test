@echo off
setlocal EnableExtensions
chcp 65001 >nul
rem To-Do 서버를 WSL에서 시작하고 브라우저로 화면을 연다.
rem 이 파일은 프로젝트 폴더에 두고, 바탕화면에는 "바로 가기"를 만들어 쓴다.
call :locate
if errorlevel 1 goto :finish

wsl.exe -d %DISTRO% --cd "%LINUX_DIR%" -- test -x .venv/bin/python
if errorlevel 1 (
  echo 가상 환경이 없습니다. README.md 의 "설치" 절을 따라 .venv 를 먼저 만들어 주세요.
  goto :finish
)
wsl.exe -d %DISTRO% --cd "%LINUX_DIR%" -- env PYTHONPATH=src .venv/bin/python -m todo_api.launcher start

:finish
echo.
pause
exit /b

:locate
rem 이 파일의 위치에서 WSL 배포판 이름과 리눅스 경로를 알아낸다.
rem 위치는 WSL 네트워크 경로여야 한다: 맨 앞 구분자 두 개 뒤가 wsl.localhost 또는 wsl$
set "HERE=%~dp0"
set "HOST_PREFIX=%HERE:~2,4%"
if /i "%HOST_PREFIX%"=="wsl." goto :parse
if /i "%HOST_PREFIX%"=="wsl$" goto :parse
goto :not_wsl
:parse
set "DISTRO="
set "REST="
for /f "tokens=1,2,* delims=\" %%a in ("%HERE%") do (
  set "DISTRO=%%b"
  set "REST=%%c"
)
if not defined DISTRO goto :not_wsl
if not defined REST goto :not_wsl
set "LINUX_DIR=/%REST:\=/%"
exit /b 0
:not_wsl
echo 이 파일은 WSL 안의 프로젝트 폴더에 두고 실행해야 합니다.
echo 다른 곳에서 쓰려면 파일을 복사하지 말고 "바로 가기"를 만들어 주세요.
exit /b 1
