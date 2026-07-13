@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   DocsConverter - Build Windows Executable
echo ============================================
echo.

:: Check virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv
    echo Run: python -m venv .venv
    echo Then: .venv\Scripts\pip install -e ".[ui,dev]"
    pause
    exit /b 1
)

set PYTHON=.venv\Scripts\python.exe

:: Ensure PyInstaller is installed
%PYTHON% -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing PyInstaller...
    %PYTHON% -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install PyInstaller
        pause
        exit /b 1
    )
)

:: Run tests first
echo [1/3] Running tests...
%PYTHON% -m pytest tests/ -v --tb=short
if %errorlevel% neq 0 (
    echo [ERROR] Tests failed. Fix them before building.
    pause
    exit /b 1
)
echo.

:: Clean previous build
echo [2/3] Cleaning previous build...
if exist "dist\DocsConverter" rmdir /s /q "dist\DocsConverter"
echo.

:: Build
echo [3/3] Building executable...
%PYTHON% -m PyInstaller docsconverter.spec --noconfirm
if %errorlevel% neq 0 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   BUILD SUCCESSFUL
echo   Output: dist\DocsConverter\DocsConverter.exe
echo ============================================
echo.
echo You can distribute the entire dist\DocsConverter folder.
echo Double-click DocsConverter.exe to launch the app.
echo.
pause
endlocal
