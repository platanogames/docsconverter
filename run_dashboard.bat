@echo off
setlocal
cd /d "%~dp0"

echo [DocsConverter] Iniciando...

:: Verificar si existe el entorno virtual
if exist ".venv\Scripts\python.exe" (
    echo [OK] Entorno virtual detectado.
    .venv\Scripts\python.exe -m app.main ui
) else (
    :: Intentar con el python del sistema
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo [WARN] Entorno virtual no detectado. Usando Python del sistema...
        python -m app.main ui
    ) else (
        echo [ERROR] No se encontro Python ni entorno virtual.
        echo Por favor, sigue las instrucciones de README.md para la instalacion.
        pause
    )
)

endlocal
