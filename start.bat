@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

rem ═══════════════════════════════════════════════════════════════════════════
rem  codebase-memory-mcp Docker 실행 스크립트
rem
rem  사용법:
rem    start.bat                      서버 기동 (이미지 없으면 자동 빌드)
rem    start.bat build                이미지 강제 재빌드 후 기동
rem    start.bat stop                 컨테이너 중지 및 제거
rem    start.bat restart              중지 후 재기동
rem    start.bat logs                 실시간 로그 출력
rem    start.bat index <경로>          저장소 인덱싱 (CLI 모드, 서버 불필요)
rem    start.bat status               컨테이너·이미지 상태 출력
rem ═══════════════════════════════════════════════════════════════════════════

set IMAGE=codebase-memory-mcp:latest
set CONTAINER=codebase-memory
set PORT=9748
set VOLUME=cbm-data
set CMD=%~1

if "%CMD%"=="" goto :do_start
if /i "%CMD%"=="build"   goto :do_build_start
if /i "%CMD%"=="stop"    goto :do_stop
if /i "%CMD%"=="restart" goto :do_restart
if /i "%CMD%"=="logs"    goto :do_logs
if /i "%CMD%"=="index"   goto :do_index
if /i "%CMD%"=="status"  goto :do_status

echo 알 수 없는 명령: %CMD%
echo 사용법: start.bat [build^|stop^|restart^|logs^|index ^<경로^>^|status]
exit /b 1

rem ── 이미지 빌드 ────────────────────────────────────────────────────────────
:build_image
echo [빌드] 이미지 빌드 중...
docker build -t %IMAGE% "%~dp0"
if errorlevel 1 (
    echo [오류] 이미지 빌드 실패
    exit /b 1
)
echo [빌드] 완료: %IMAGE%
exit /b 0

rem ── 기존 컨테이너 정리 ─────────────────────────────────────────────────────
:remove_container
docker inspect %CONTAINER% >nul 2>&1
if not errorlevel 1 (
    echo [정리] 기존 컨테이너 중지·제거 중...
    docker stop %CONTAINER% >nul 2>&1
    docker rm   %CONTAINER% >nul 2>&1
)
exit /b 0

rem ── 서버 기동 ──────────────────────────────────────────────────────────────
:run_container
docker run -d ^
  --name %CONTAINER% ^
  -p %PORT%:%PORT% ^
  -v %VOLUME%:/data ^
  --restart unless-stopped ^
  %IMAGE%
if errorlevel 1 (
    echo [오류] 컨테이너 기동 실패
    exit /b 1
)
echo.
echo  기동 완료
echo  MCP HTTP  : http://localhost:%PORT%/mcp
echo  헬스체크  : http://localhost:%PORT%/mcp/health
echo  로그 확인 : start.bat logs
echo  인덱싱    : start.bat index "C:\path\to\project"
echo.
exit /b 0

rem ── [start] ─────────────────────────────────────────────────────────────────
:do_start
docker image inspect %IMAGE% >nul 2>&1
if errorlevel 1 (
    echo [*] 이미지가 없습니다. 먼저 빌드합니다...
    call :build_image
    if errorlevel 1 exit /b 1
)
call :remove_container
call :run_container
goto :eof

rem ── [build] ──────────────────────────────────────────────────────────────────
:do_build_start
call :build_image
if errorlevel 1 exit /b 1
call :remove_container
call :run_container
goto :eof

rem ── [stop] ───────────────────────────────────────────────────────────────────
:do_stop
echo [중지] 컨테이너 중지 중...
docker stop %CONTAINER% >nul 2>&1
docker rm   %CONTAINER% >nul 2>&1
echo [중지] 완료
goto :eof

rem ── [restart] ────────────────────────────────────────────────────────────────
:do_restart
call :do_stop
call :do_start
goto :eof

rem ── [logs] ───────────────────────────────────────────────────────────────────
:do_logs
echo [로그] Ctrl+C 로 종료
docker logs -f %CONTAINER%
goto :eof

rem ── [status] ─────────────────────────────────────────────────────────────────
:do_status
echo.
echo ── 이미지 ──────────────────────────────────────────────────────────────────
docker image inspect %IMAGE% --format "  이름: {{.RepoTags}}  크기: {{.Size}}  생성: {{.Created}}" 2>nul || echo   (없음)
echo.
echo ── 컨테이너 ────────────────────────────────────────────────────────────────
docker inspect %CONTAINER% --format "  ID: {{.Id}}  상태: {{.State.Status}}  포트: {{.NetworkSettings.Ports}}" 2>nul || echo   (없음)
echo.
echo ── 볼륨 ────────────────────────────────────────────────────────────────────
docker volume inspect %VOLUME% --format "  이름: {{.Name}}  경로: {{.Mountpoint}}" 2>nul || echo   (없음)
echo.
goto :eof

rem ── [index] ──────────────────────────────────────────────────────────────────
:do_index
set WORKSPACE=%~2
if "%WORKSPACE%"=="" (
    echo [오류] 인덱싱할 프로젝트 경로를 지정하세요.
    echo 사용법: start.bat index "C:\path\to\project"
    exit /b 1
)

rem 이미지 확인
docker image inspect %IMAGE% >nul 2>&1
if errorlevel 1 (
    echo [*] 이미지가 없습니다. 먼저 빌드합니다...
    call :build_image
    if errorlevel 1 exit /b 1
)

rem 마지막 폴더명을 프로젝트 이름으로 사용
for %%F in ("%WORKSPACE%") do set PROJECT_NAME=%%~nxF

echo [인덱싱] %WORKSPACE% (프로젝트명: %PROJECT_NAME%)
echo [인덱싱] 완료 후 start.bat 으로 서버를 기동하세요.
echo.

docker run --rm ^
  -v %VOLUME%:/data ^
  -v "%WORKSPACE%:/workspace:ro" ^
  %IMAGE% ^
  cli index_repository "{\"path\":\"/workspace\",\"name\":\"%PROJECT_NAME%\"}"

if errorlevel 1 (
    echo.
    echo [오류] 인덱싱 실패
    exit /b 1
)
echo.
echo [인덱싱] 완료. start.bat 으로 서버를 기동하세요.
goto :eof
