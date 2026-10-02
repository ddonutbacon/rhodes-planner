@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo Rhodes Planner - Anaconda Launcher
echo ============================================
echo.

set "CONDA_ACTIVATE="

REM 1) If conda is already available in this shell
where conda >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%i in ('where conda') do (
        set "CONDA_EXE=%%i"
        goto :conda_found_path
    )
)

REM 2) Search common Anaconda/Miniconda locations
if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
    set "CONDA_ACTIVATE=%USERPROFILE%\anaconda3\Scripts\activate.bat"
    goto :activate_base
)

if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
    set "CONDA_ACTIVATE=%USERPROFILE%\miniconda3\Scripts\activate.bat"
    goto :activate_base
)

if exist "C:\ProgramData\anaconda3\Scripts\activate.bat" (
    set "CONDA_ACTIVATE=C:\ProgramData\anaconda3\Scripts\activate.bat"
    goto :activate_base
)

if exist "C:\ProgramData\miniconda3\Scripts\activate.bat" (
    set "CONDA_ACTIVATE=C:\ProgramData\miniconda3\Scripts\activate.bat"
    goto :activate_base
)

echo Could not automatically find Anaconda/Miniconda.
echo.
echo Please:
echo   1. Open "Anaconda Prompt"
echo   2. cd to this Rhodes Planner folder
echo   3. Run: run_windows_anaconda.bat
echo.
pause
exit /b 1

:conda_found_path
REM conda command is already visible; initialize through its parent activate if possible
for %%d in ("%CONDA_EXE%") do set "CONDA_DIR=%%~dpd"
if exist "%CONDA_DIR%activate.bat" (
    set "CONDA_ACTIVATE=%CONDA_DIR%activate.bat"
    goto :activate_base
)

REM Fall back to direct conda command if already initialized
goto :create_env

:activate_base
call "%CONDA_ACTIVATE%"
if errorlevel 1 goto :error

:create_env
echo Checking environment...
call conda env list | findstr /R /C:"^rhodes-planner " >nul 2>&1
if errorlevel 1 (
    echo Creating conda environment "rhodes-planner" with Python 3.12...
    call conda create -n rhodes-planner python=3.12 -y
    if errorlevel 1 goto :error
)

echo Activating environment...
call conda activate rhodes-planner
if errorlevel 1 goto :error

echo.
echo Python:
python --version
if errorlevel 1 goto :error

echo.
echo Installing/updating dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :error

pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo Starting Rhodes Planner...
echo Browser address: http://localhost:8501
echo.
streamlit run app\main.py --server.address=127.0.0.1
goto :eof

:error
echo.
echo ============================================
echo Rhodes Planner failed to start.
echo Copy the error text above and send it back.
echo ============================================
pause
exit /b 1
