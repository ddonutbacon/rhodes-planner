@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%USERPROFILE%\miniconda3\python.exe"
if exist "%PYTHON%" goto run
set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
if exist "%PYTHON%" goto run
set "PYTHON=C:\ProgramData\miniconda3\python.exe"
if exist "%PYTHON%" goto run
set "PYTHON=C:\ProgramData\anaconda3\python.exe"
if exist "%PYTHON%" goto run

echo Miniconda/Anaconda Python was not found in common locations.
pause
exit /b 1

:run
"%PYTHON%" -m streamlit run app\main.py --server.address 127.0.0.1 --browser.gatherUsageStats false
endlocal
