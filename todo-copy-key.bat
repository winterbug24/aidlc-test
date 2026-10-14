@echo off
setlocal EnableExtensions
chcp 65001 >nul
rem 저장된 API 키를 클립보드에 복사한다. 키 값은 창에 표시하지 않는다.
call :locate
if errorlevel 1 goto :finish

wsl.exe %DISTRO_ARGS% --cd "%LINUX_DIR%" -- test -x .venv/bin/python
if errorlevel 1 (
  echo 가상 환경이 없습니다. README.md 의 "설치" 절을 따라 .venv 를 먼저 만들어 주세요.
  goto :finish
)
wsl.exe %DISTRO_ARGS% --cd "%LINUX_DIR%" -- env PYTHONPATH=src .venv/bin/python -m todo_api.launcher copy-key

:finish
echo.
pause
exit /b

:locate
rem 이 파일의 위치에서 WSL 배포판과 리눅스 경로를 알아낸다. 지원하는 위치:
rem - WSL 네트워크 경로: \\wsl.localhost\배포판\... 또는 \\wsl$\배포판\... (그 배포판 사용)
rem - 드라이브 경로: D:\... 는 /mnt/d/... (기본 배포판 사용)
rem 어느 경우든 같은 폴더에 src\todo_api 가 있어야 프로젝트 폴더로 본다.
set "HERE=%~dp0"
if not exist "%HERE%src\todo_api\" goto :not_project
set "DISTRO_ARGS="
if "%HERE:~1,1%"==":" goto :drive
set "HOST_PREFIX=%HERE:~2,4%"
if /i "%HOST_PREFIX%"=="wsl." goto :parse
if /i "%HOST_PREFIX%"=="wsl$" goto :parse
goto :not_project
:drive
set "DRIVE=%HERE:~0,1%"
rem WSL은 드라이브를 소문자 이름으로 연결한다 (D: -> /mnt/d)
for %%L in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do if /i "%DRIVE%"=="%%L" set "DRIVE=%%L"
set "REST=%HERE:~3%"
set "LINUX_DIR=/mnt/%DRIVE%/%REST:\=/%"
exit /b 0
:parse
set "DISTRO="
set "REST="
for /f "tokens=1,2,* delims=\" %%a in ("%HERE%") do (
  set "DISTRO=%%b"
  set "REST=%%c"
)
if not defined DISTRO goto :not_project
if not defined REST goto :not_project
set "DISTRO_ARGS=-d %DISTRO%"
set "LINUX_DIR=/%REST:\=/%"
exit /b 0
:not_project
echo 이 파일은 프로젝트 폴더(WSL 안 또는 D:\ 같은 드라이브의 폴더)에 두고 실행해야 합니다.
echo 다른 곳에서 쓰려면 파일을 복사하지 말고 "바로 가기"를 만들어 주세요.
exit /b 1
