@echo off
setlocal

cd /d "%~dp0"

set PROFILE=configs/profiles/fixtures-complex.yaml
set PYTHON_EXE=
set PAUSE_ON_END=1

if /I "%~1"=="--no-pause" set PAUSE_ON_END=0

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
  where py >nul 2>nul
  if %errorlevel%==0 (
    set "PYTHON_EXE=py -3"
  ) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
      set "PYTHON_EXE=python"
    )
  )
)

if "%PYTHON_EXE%"=="" (
  echo No se encontro Python ni .venv\Scripts\python.exe
  echo Instala Python o crea la venv del proyecto.
  if "%PAUSE_ON_END%"=="1" pause
  exit /b 2
)

echo == Ejecutando conversion de fixtures complejos ==
echo Interpreter: %PYTHON_EXE%
echo.

call %PYTHON_EXE% -c "import yaml" >nul 2>nul
if errorlevel 1 (
  echo Falta dependencia: PyYAML ^(modulo 'yaml'^).
  echo Instala dependencias con:
  echo   %PYTHON_EXE% -m pip install -e ".[dev,ui]"
  echo O minimo:
  echo   %PYTHON_EXE% -m pip install pyyaml
  if "%PAUSE_ON_END%"=="1" pause
  exit /b 3
)

call %PYTHON_EXE% -m app.main convert --input fixtures/complex_markdown/01-corporate-report.md --profile %PROFILE%
if errorlevel 1 goto :fail

call %PYTHON_EXE% -m app.main convert --input fixtures/complex_markdown/02-technical-rfc.md --profile %PROFILE%
if errorlevel 1 goto :fail

call %PYTHON_EXE% -m app.main convert --input fixtures/complex_markdown/03-knowledge-base.md --profile %PROFILE%
if errorlevel 1 goto :fail

call %PYTHON_EXE% -m app.main convert --input fixtures/complex_markdown/04-release-notes-heavy.md --profile %PROFILE%
if errorlevel 1 goto :fail

echo.
echo Ejecucion completada.
if "%PAUSE_ON_END%"=="1" pause
exit /b 0

:fail
echo.
echo Fallo una conversion. Revisa los logs.
if "%PAUSE_ON_END%"=="1" pause
exit /b 1
