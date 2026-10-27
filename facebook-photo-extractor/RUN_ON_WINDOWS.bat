@echo off
setlocal
title Facebook Photo Extractor - No API
cd /d "%~dp0"
echo ===============================================
echo    FACEBOOK PHOTO EXTRACTOR - NO META API
echo ===============================================
echo.
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python 3 is not installed.
        echo Download it from https://www.python.org/downloads/
        echo Enable "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)
if not "%~1"=="" (
    set "SOURCE=%~1"
) else (
    echo Paste the complete path of the saved Facebook HTML or TXT file.
    echo Tip: You can also drag the file onto this BAT file.
    set /p "SOURCE=File path: "
)
REM Remove quotes pasted from Windows Copy as path. The Python invocation adds its own.
set "SOURCE=%SOURCE:"=%"
if not defined SOURCE (
    echo No HTML file specified.
    pause
    exit /b 1
)
if not exist "%SOURCE%" (
    echo File not found: "%SOURCE%"
    echo Check the full path and try again.
    pause
    exit /b 1
)
echo.
%PYTHON% "%~dp0offline_extract.py" "%SOURCE%"
if errorlevel 1 (
    echo.
    echo Extraction did not finish successfully. Check the error details above.
    pause
    exit /b 1
)
echo.
echo Finished. Check the output folder beside your saved HTML file.
pause
