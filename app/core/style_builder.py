from __future__ import annotations

from app.core.models import StyleOptions


def build_override_css(options: StyleOptions) -> str:
    is_dark = options.document_theme == "dark"
    bg_color = "#0f172a" if is_dark else "#ffffff"
    body_text = options.text_color

    # List spacing
    list_margin = {"compact": "0.15em", "normal": "0.4em", "spacious": "0.8em"}.get(
        options.list_spacing, "0.4em"
    )

    # Table density
    cell_padding = {"compact": "4px 6px", "normal": "8px 12px", "spacious": "12px 18px"}.get(
        options.table_density, "8px 12px"
    )

    zebra_rule = ""
    if options.zebra_tables:
        stripe = "#1e293b" if is_dark else "#f8fafc"
        zebra_rule = f"  tbody tr:nth-child(even) {{ background: {stripe}; }}\n"

    css = f"""/* DocsConverter override - generated */
body {{
  background: {bg_color};
  color: {body_text};
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  line-height: 1.65;
  text-align: {options.text_align};
}}
h1, h2, h3, h4, h5, h6 {{
  color: {options.title_color};
  text-align: {options.heading_align};
}}
a {{
  color: {options.accent_color};
}}
table {{
  border-collapse: collapse;
  width: 100%;
  border: 1px solid {options.table_border_color};
}}
th {{
  background: {options.table_header_bg};
  color: {options.title_color};
  padding: {cell_padding};
  border: 1px solid {options.table_border_color};
  text-align: left;
}}
td {{
  padding: {cell_padding};
  border: 1px solid {options.table_border_color};
}}
{zebra_rule}ul, ol {{
  margin-top: {list_margin};
  margin-bottom: {list_margin};
}}
li {{
  margin-bottom: {list_margin};
}}
"""
    return css
