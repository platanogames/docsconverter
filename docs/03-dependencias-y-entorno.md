# Dependencias y Configuración del Entorno

DocsConverter requiere una combinación de herramientas de procesamiento de texto y un entorno Python configurado.

## Requisitos Externos
1. **Pandoc (3.x):** Es el motor principal de conversión.
2. **Motores PDF:**
   - Para modo `web`: `wkhtmltopdf`.
   - Para modo `native`: Una distribución de LaTeX (como MiKTeX o TeX Live).

## Configuración del Entorno Python
Se recomienda el uso de Python 3.11+.

```bash
# Crear entorno virtual
python -m venv .venv
# Instalar dependencias
pip install -e ".[ui,ux]"
```

## Lanzamiento Rápido (Windows)
Para facilitar el uso en entornos Windows, se ha incluido el script:
- `run_dashboard.bat`: Detecta automáticamente el entorno virtual `.venv` y lanza la interfaz gráfica sin necesidad de comandos manuales.

## Detección de Pandoc
La aplicación busca `pandoc.exe` en:
1. El PATH del sistema.
2. La carpeta local `pandoc-3.9-windows-x86_64/pandoc-3.9/`.
3. Una ruta personalizada definida en la pestaña de **Configuración** del Dashboard.
