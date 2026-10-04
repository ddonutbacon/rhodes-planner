@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=.venv\Scripts\python.exe"
if exist "%PYTHON%" goto run

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYTHON=py"
    goto run
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYTHON=python"
    goto run
)

echo Python was not found. For non-technical use, download the portable Windows release instead.
pause
exit /b 1

:run
%PYTHON% -m streamlit run app\main.py --server.address 127.0.0.1 --browser.gatherUsageStats false
endlocal
