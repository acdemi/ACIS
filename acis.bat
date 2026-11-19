@echo off
rem ACIS unified launcher for Windows cmd (ASCII-only to stay parser-safe).
rem Docker mode wraps docker compose (start/stop/status/logs/import).
rem Local mode delegates to scripts\start_acis.ps1 (local start/stop).
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%" || (
  echo [ACIS] cannot enter project directory: %ROOT%
  exit /b 1
)

rem Bypass any system proxy (e.g. Clash) that hijacks httpx calls to localhost
rem and makes Docker-published local services (Qdrant 6333) return 502.
set "NO_PROXY=localhost,127.0.0.1"
set "no_proxy=localhost,127.0.0.1"

set "ACTION=%~1"
if not defined ACTION set "ACTION=start"
set "LOCAL_ACTION=%~2"
set "PORT_VALUE="

if /i "%ACTION%"=="start"  goto :docker_start
if /i "%ACTION%"=="stop"   goto :docker_stop
if /i "%ACTION%"=="status" goto :docker_status
if /i "%ACTION%"=="logs"   goto :docker_logs
if /i "%ACTION%"=="import" goto :docker_import
if /i "%ACTION%"=="local"  goto :local
if /i "%ACTION%"=="help"   goto :usage
if /i "%ACTION%"=="-h"     goto :usage
if /i "%ACTION%"=="--help" goto :usage

echo [ACIS] unknown command: %ACTION%
goto :usage_error

rem ---------------------------------------------------------------- Docker mode

:docker_start
call :require_docker || goto :fail
docker compose up -d --build
if errorlevel 1 goto :fail
call :wait_healthy || goto :fail
call :show_hints
goto :done

:docker_stop
call :require_docker || goto :fail
docker compose down
if errorlevel 1 goto :fail
echo [ACIS] stopped (data volumes kept). To wipe data: docker compose down -v
goto :done

:docker_status
call :require_docker || goto :fail
docker compose ps
if errorlevel 1 goto :fail
goto :done

:docker_logs
call :require_docker || goto :fail
docker compose logs -f api
goto :done

:docker_import
call :require_docker || goto :fail
if not exist "data\Agriculture_KnowledgeGraph-master" (
  echo [ACIS] data\Agriculture_KnowledgeGraph-master not found; skipping import.
  echo        Unpack AgriKG data there and re-run: acis.bat import
  goto :done
)
docker compose exec api python scripts/import_agrikg.py --yes
if errorlevel 1 goto :fail
goto :done

rem ----------------------------------------------------------------- Local mode

:local
if not defined LOCAL_ACTION set "LOCAL_ACTION=start"
if /i "%LOCAL_ACTION%"=="start" goto :local_port
if /i "%LOCAL_ACTION%"=="stop"  goto :local_run
if /i "%LOCAL_ACTION%"=="help"  goto :usage
echo [ACIS] local accepts only start or stop, got: %LOCAL_ACTION%
goto :usage_error

:local_port
if /i "%~3"=="-Port"  goto :local_port_next
if /i "%~3"=="--port" goto :local_port_next
if not "%~3"=="" set "PORT_VALUE=%~3"
goto :local_port_check
:local_port_next
set "PORT_VALUE=%~4"
:local_port_check
if not defined PORT_VALUE goto :local_run
echo %PORT_VALUE%| findstr /r "^[1-9][0-9]*$" >nul
if errorlevel 1 (
  echo [ACIS] port must be a number in 1-65535, got: %PORT_VALUE%
  goto :usage_error
)

:local_run
set "LOCAL_SCRIPT=%ROOT%scripts\start_acis.ps1"
if not exist "%LOCAL_SCRIPT%" (
  echo [ACIS] local launcher not found: %LOCAL_SCRIPT%
  goto :fail
)
set "PS_ARGS=-Action %LOCAL_ACTION%"
if defined PORT_VALUE set "PS_ARGS=-Action %LOCAL_ACTION% -Port %PORT_VALUE%"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%LOCAL_SCRIPT%" %PS_ARGS%
if errorlevel 1 goto :fail
goto :done

rem --------------------------------------------------------------------- Helpers

:require_docker
docker info >nul 2>&1
if errorlevel 1 (
  echo [ACIS] Docker is not running. Start Docker Desktop first.
  exit /b 1
)
exit /b 0

:health_ready
where curl.exe >nul 2>&1
if errorlevel 1 goto :health_ready_ps
curl.exe -sf --max-time 3 http://localhost:8000/health >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0
:health_ready_ps
powershell.exe -NoLogo -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { exit 0 } } catch { } exit 1"
exit /b %ERRORLEVEL%

:wait_healthy
echo [ACIS] waiting for API health (http://localhost:8000/health) ...
set "HEALTH_TRIES=0"
:wait_healthy_loop
ping -n 3 127.0.0.1 >nul 2>&1
call :health_ready
if not errorlevel 1 (
  echo [ACIS] API ready.
  exit /b 0
)
set /a HEALTH_TRIES+=1
if %HEALTH_TRIES% lss 30 goto :wait_healthy_loop
echo [ACIS] API did not become ready in 60s; check logs: acis.bat logs
exit /b 1

:show_hints
echo.
echo ============================================
echo   ACIS is up
echo   API:          http://localhost:8000   (GET /health, POST /diagnose)
echo   Neo4j console: http://localhost:17474
echo   Qdrant:       http://localhost:6333
echo ============================================
echo.
echo Tips:
echo   - Set ACIS_API_KEY and NEO4J_PASSWORD in .env; do not commit secrets
echo   - API is bound to localhost; send X-API-Key for diagnosis requests
echo   - Enable LLM Judge/Critic by setting DEEPSEEK_API_KEY before start
echo   - Import real AgriKG graph:  acis.bat import
echo   - Stop:                      acis.bat stop
echo   - Local native mode:         acis.bat local start
exit /b 0

:usage
echo ACIS one-click launcher (Windows cmd)
echo.
echo Usage: acis.bat [command]
echo.
echo   start            Docker Compose up (build + wait healthy); default command
echo   stop             Stop Docker services (data volumes kept)
echo   status           Show Docker service status
echo   logs             Follow API container logs
echo   import           Import the AgriKG graph into Neo4j (optional)
echo.
echo   local start      Start the native local launcher (127.0.0.1, opens browser)
echo   local stop       Stop the process started by the local launcher
echo   local start 8010 Use a custom local port (or set ACIS_LOCAL_PORT)
echo.
echo   help             Show this help
echo.
echo Notes: Docker mode needs Docker Desktop and ACIS_API_KEY / NEO4J_PASSWORD in .env.
echo        Local mode needs Python 3.11+, a built web\dist, and ACIS_API_KEY in .env.
echo        Linux / macOS keep using ./start.sh; local logic lives in scripts\start_acis.ps1.
goto :done

:usage_error
echo Run: acis.bat help
exit /b 1

:fail
echo [ACIS] command failed (exit code %ERRORLEVEL%).
exit /b 1

:done
exit /b 0
