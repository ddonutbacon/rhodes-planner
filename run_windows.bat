@echo off
setlocal
cd /d "%~dp0"

REM Prefer normal Python if available.
where python >nul 2>&1
if %errorlevel%==0 goto :normal_python

where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py"
    goto :venv
)

REM Fall back to Anaconda launcher if present.
if exist "run_windows_anaconda.bat" (
    echo Standard Python was not found.
    echo Trying the Anaconda launcher instead...
    call run_windows_anaconda.bat
    exit /b %errorlevel%
)

echo Python was not found.
echo If you use Anaconda, open Anaconda Prompt and run run_windows_anaconda.bat
pause
exit /b 1

:normal_python
set "PY=python"

:venv
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 goto :error
)

call .venv\Scripts\activate.bat

echo Installing/updating dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto :error

echo Starting Rhodes Planner...
streamlit run app\main.py --server.address=127.0.0.1
goto :eof

:error
echo.
echo Something failed. Copy the text above and send it back for debugging.
pause
