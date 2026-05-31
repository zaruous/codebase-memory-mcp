@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

rem ═══════════════════════════════════════════════════════════════════════════
rem  codebase-memory-mcp Docker 이미지 빌드
rem
rem  사용법:
rem    dockerBuild.bat              기본 버전(0.10.1)으로 빌드
rem    dockerBuild.bat 0.10.1       버전 지정 빌드
rem ═══════════════════════════════════════════════════════════════════════════

set IMAGE=codebase-memory-mcp
set VERSION=%~1
if "%VERSION%"=="" set VERSION=0.10.1

echo [빌드] %IMAGE%:%VERSION% 빌드 시작...
echo.

docker build ^
  --build-arg VERSION=%VERSION% ^
  -t %IMAGE%:%VERSION% ^
  -t %IMAGE%:latest ^
  "%~dp0"

if errorlevel 1 (
    echo.
    echo [오류] 빌드 실패
    exit /b 1
)

echo.
echo [완료] 빌드 성공
echo   이미지: %IMAGE%:%VERSION%
echo   이미지: %IMAGE%:latest
