# Stack Tecnológico y UX Dashboard

El Dashboard de DocsConverter está diseñado para ofrecer una experiencia de usuario fluida y profesional, alejándose de la complejidad técnica de Pandoc y ofreciendo un flujo de trabajo visual.

## Stack de UI
- **Framework:** PySide6 (Qt para Python).
- **Estilo:** CSS dinámico inyectado (QSS) con soporte para temas.
- **Iconografía:** Emojis Unicode estándar para máxima portabilidad sin dependencias de assets externos.

## Mejoras Recientes de UX
### 1. Organización por Pestañas
Se ha implementado una separación clara entre los modos de operación:
- **Archivo Único:** Para conversiones rápidas de un solo documento.
- **Conversión por Lote:** Para procesar directorios enteros con patrones de búsqueda glob.

### 2. Agrupación Lógica de Campos
Para reducir la carga cognitiva, los parámetros se agrupan en:
- **Metadatos:** Títulos, autores, versiones y clasificación de seguridad.
- **Formatos de Salida:** Selección de rutas para HTML, PDF, DOCX y EPUB.
- **Motores y Reglas:** Configuración avanzada de Pandoc y normalización de Markdown.

### 3. Soporte Drag & Drop
El dashboard acepta el arrastre de archivos:
- Al soltar un `.md`, se carga automáticamente como entrada.
- Al soltar un `.yaml` o `.yml`, se carga como perfil de configuración.

### 4. Botón de Acción Unificado
Un botón de "Convertir" prominente que ajusta su comportamiento según la pestaña activa, facilitando la ejecución inmediata.
