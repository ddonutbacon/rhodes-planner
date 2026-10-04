@echo off
setlocal

rem Always resolve files relative to this launcher, never the caller's working directory.
set "APP_ROOT=%~dp0"
set "PYTHON=%APP_ROOT%runtime\python.exe"
set "LAUNCHER=%APP_ROOT%app\launcher.py"

if not exist "%PYTHON%" (
    echo.
    echo ERROR: Portable Python runtime not found.
    echo Expected:
    echo %PYTHON%
    echo.
    echo Keep the runtime folder beside this launcher.
    pause
    exit /b 1
)

if not exist "%LAUNCHER%" (
    echo.
    echo ERROR: Rhodes Planner launcher is missing.
    echo Expected:
    echo %LAUNCHER%
    echo.
    pause
    exit /b 1
)

"%PYTHON%" "%LAUNCHER%"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
    echo.
    echo Rhodes Planner exited with code %EXITCODE%.
    pause
)

endlocal & exit /b %EXITCODE%
