@echo off
setlocal
title F.A.C.E Backend Launcher

set "BACKEND_DIR=%~dp0"
set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
set "MYSQL_EXE=C:\xampp\mysql\bin\mysqld.exe"
set "MYSQL_CONFIG=C:\xampp\mysql\bin\my.ini"

if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
if not exist "%MYSQL_EXE%" goto mysql_missing

pushd "%BACKEND_DIR%"
echo Starting F.A.C.E backend services in order...

call :port_ready 3306
if errorlevel 1 (
    echo MySQL is not running. Starting XAMPP MySQL...
    start "F.A.C.E MySQL" /min "%MYSQL_EXE%" --defaults-file="%MYSQL_CONFIG%" --standalone
    call :wait_for_port 3306 "MySQL"
    if errorlevel 1 goto startup_failed
) else (
    echo MySQL is already listening on port 3306.
)

call :service_ready 5000 face_api
if errorlevel 1 (
    call :port_ready 5000
    if not errorlevel 1 (
        echo ERROR: Port 5000 is occupied by another service.
        goto startup_failed
    )
    echo Starting the F.A.C.E management API on port 5000...
    start "F.A.C.E Management API - port 5000" "%PYTHON_EXE%" -u main.py
    call :wait_for_service 5000 face_api "F.A.C.E management API"
    if errorlevel 1 goto startup_failed
) else (
    echo F.A.C.E management API is already running on port 5000.
)

call :service_ready 5001 esp_api
if errorlevel 1 (
    call :port_ready 5001
    if not errorlevel 1 (
        echo ERROR: Port 5001 is occupied by a service other than the F.A.C.E ESP API.
        goto startup_failed
    )
    echo Starting ESP32 upload, recognition, and attendance API on port 5001...
    start "F.A.C.E ESP API - port 5001" "%PYTHON_EXE%" -u esp-server.py
    call :wait_for_service 5001 esp_api "ESP API"
    if errorlevel 1 goto startup_failed
) else (
    echo ESP32 API is already running on port 5001.
)

call :process_running register.py
if errorlevel 1 (
    echo Starting the student-registration image watcher...
    start "F.A.C.E Student Registration" "%PYTHON_EXE%" -u register.py
) else (
    echo Student-registration image watcher is already running.
)

echo.
echo Backend is running:
echo   Attendance management API: http://localhost:5000
echo   ESP32 upload API: http://localhost:5001/upload
echo   Student registration watcher: monitors backend\captured_faces for enrollment images.
echo   Attendance sessions: start and stop through the management API.
echo   Recognition runs inside the ESP32 upload API; do not run recognition.py separately.
echo.
popd
pause
exit /b 0

:port_ready
powershell -NoProfile -Command "$c = New-Object Net.Sockets.TcpClient; try { $c.Connect('127.0.0.1', %~1); exit 0 } catch { exit 1 } finally { $c.Close() }" >nul 2>&1
exit /b %errorlevel%

:service_ready
powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:%~1/health' -TimeoutSec 1; if ($r.service -eq '%~2' -and $r.status -eq 'ok') { exit 0 } } catch {}; exit 1" >nul 2>&1
exit /b %errorlevel%

:process_running
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*%~1*' }; if ($p) { exit 0 } else { exit 1 }" >nul 2>&1
exit /b %errorlevel%

:wait_for_port
for /L %%I in (1,1,30) do (
    call :port_ready %~1
    if not errorlevel 1 exit /b 0
    timeout /t 1 /nobreak >nul
)
echo ERROR: %~2 did not become ready on port %~1.
exit /b 1

:wait_for_service
for /L %%I in (1,1,30) do (
    call :service_ready %~1 %~2
    if not errorlevel 1 exit /b 0
    timeout /t 1 /nobreak >nul
)
echo ERROR: %~3 did not become ready on port %~1.
exit /b 1

:startup_failed
echo.
echo Startup stopped because a required service did not become ready.
echo Check the service window for its error message, then run this file again.
popd
pause
exit /b 1

:mysql_missing
echo ERROR: XAMPP MySQL was not found at "%MYSQL_EXE%".
echo Start MySQL in XAMPP Control Panel, then run this file again.
pause
exit /b 1
