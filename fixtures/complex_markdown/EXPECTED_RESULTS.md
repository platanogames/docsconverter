# Expected Results (Oracle)

Este documento define como debe verse el resultado para validar conversiones.

## Global Expectations

1. Encabezados sin espacio (`#Title`) deben quedar normalizados (`# Title`) en el markdown limpio.
2. Code fences de 4 backticks deben quedar en 3 backticks en el markdown limpio.
3. Links `www.*` deben convertirse a `https://www.*` cuando `sanitize_links=true`.
4. HTML debe renderizar tablas, listas, blockquotes y bloques de codigo sin perdida de contenido.
5. Historial debe registrar una fila por salida (`html` y/o `pdf`) con `return_code`.

## File-specific Expectations

### 01-corporate-report.md

- Encabezados `#Executive Summary` y `##Highlights` deben aparecer con espacio.
- Link `www.internal-board.example` debe quedar con `https://`.
- Tabla "Progress Table" debe conservar columnas y alineacion basica.

### 02-technical-rfc.md

- Titulo `#RFC-012...` debe normalizarse.
- Definiciones (`Pipeline`, `Profile`) deben renderizarse en HTML sin colapsar en texto plano.
- Link `www.arch.local/docs` debe quedar con `https://`.

### 03-knowledge-base.md

- Encabezado principal debe normalizarse.
- Comando bash multilinea debe mantenerse como bloque de codigo.
- Link `www.runbook.local/main` debe quedar con `https://`.

### 04-release-notes-heavy.md

- Encabezado principal debe normalizarse.
- Bloques powershell deben mantenerse formateados.
- Checklist de follow-up debe renderizar checkboxes en HTML.
- Link final debe quedar con `https://`.

## Pass Criteria

1. Todos los outputs HTML existen y abren correctamente.
2. Si hay motor PDF instalado, todos los outputs PDF existen.
3. No hay `return_code != 0` en historial para casos esperados.
