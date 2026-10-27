@echo off
setlocal
title Facebook Photo Viewer Quality Collector
cd /d "%~dp0"
echo ==============================================
echo   FACEBOOK VIEWER-QUALITY PHOTO COLLECTOR
echo ==============================================
echo.
echo This is DIFFERENT from the fast saved-thumbnail exporter.
echo It opens Facebook photo posts in a separate browser window
echo and collects the best matching image the viewer exposes.
echo It cannot guarantee the original camera uploads.
echo.
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python 3 is required: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set "PYTHON=python"
)
if not "%~1"=="" (
    set "SOURCE=%~1"
) else (
    echo Paste the path to the saved Facebook Photos webpage .html
    echo or drag that file onto this BAT file.
    set /p "SOURCE=Saved HTML: "
)
set "SOURCE=%SOURCE:"=%"
if not exist "%SOURCE%" (
    echo Cannot find file: "%SOURCE%"
    pause
    exit /b 1
)
echo.
set "COUNT=20"
set /p "COUNT=How many photo posts? (1-150; press Enter for 20): "
if not defined COUNT set "COUNT=20"
echo.
echo To capture higher-quality versions, Playwright and Chromium are
echo needed one time:
echo   %PYTHON% -m pip install playwright
echo   %PYTHON% -m playwright install chromium
echo.
%PYTHON% "%~dp0viewer_quality.py" "%SOURCE%" --limit %COUNT%
if errorlevel 1 (
    echo.
    echo Some photos could not be captured. Inspect the output
    echo PHOTO_POST_LINKS.html and manifest if created.
)
echo.
pause
