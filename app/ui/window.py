from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.core.batch import collect_markdown_files, retarget_outputs_for_input
from app.core.config import load_profile, save_profile
from app.core.history import read_history
from app.core.models import (
    ConversionJob,
    ConversionProfile,
    OutputTarget,
    RuleSet,
    StyleOptions,
    StyleProfile,
)
from app.core.pipeline import run_conversion_job
from app.core.preflight import preflight_or_raise
from app.core.style_builder import build_override_css


def run_ui(pandoc_path: Path) -> None:
    from PySide6.QtCore import QObject, QThread, Qt, QUrl, Signal
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressDialog,
        QPushButton,
        QScrollArea,
        QSplitter,
        QStackedWidget,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextBrowser,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    class ConversionWorker(QObject):
        progress = Signal(int, str)
        finished = Signal(object)
        failed = Signal(str)

        def __init__(
            self,
            job: ConversionJob,
            pandoc_path_value: Path,
            history_path_value: Path,
            had_configured_pdf_engine: bool,
            sanitization_config=None,
        ) -> None:
            super().__init__()
            self.job = job
            self.pandoc_path = pandoc_path_value
            self.history_path = history_path_value
            self.had_configured_pdf_engine = had_configured_pdf_engine
            self.sanitization_config = sanitization_config

        def run(self) -> None:
            try:
                self.progress.emit(5, "Validando dependencias...")
                fallback_warning: str | None = None
                try:
                    resolved_pandoc, detected_engine = preflight_or_raise(self.job, self.pandoc_path)
                except RuntimeError as exc:
                    msg = str(exc)
                    has_html = any(out.format == "html" for out in self.job.outputs)
                    has_pdf = any(out.format == "pdf" for out in self.job.outputs)
                    if has_html and has_pdf and "No se detecto motor PDF" in msg:
                        self.job.outputs = [out for out in self.job.outputs if out.format == "html"]
                        resolved_pandoc = self.pandoc_path
                        detected_engine = None
                        fallback_warning = "[warn] motor PDF no disponible; se genero solo HTML."
                    else:
                        raise

                self.progress.emit(8, "Iniciando conversion...")
                results = run_conversion_job(
                    self.job,
                    pandoc_path=resolved_pandoc,
                    history_path=self.history_path,
                    progress_callback=lambda v, m: self.progress.emit(v, m),
                    sanitization_config=self.sanitization_config,
                )
                self.progress.emit(100, "Completado.")
                self.finished.emit(
                    {
                        "results": results,
                        "detected_engine": detected_engine,
                        "fallback_warning": fallback_warning,
                        "had_configured_pdf_engine": self.had_configured_pdf_engine,
                        "pdf_mode": self.job.style_profile.pdf_layout_mode,
                        "pdf_engine": self.job.style_profile.pdf_engine,
                    }
                )
            except Exception as exc:  # pragma: no cover
                self.failed.emit(str(exc))

    class BatchConversionWorker(QObject):
        progress = Signal(int, str)
        finished = Signal(object)
        failed = Signal(str)

        def __init__(
            self,
            profile: ConversionProfile,
            input_dir: Path,
            pattern: str,
            recursive: bool,
            pandoc_path_value: Path,
            history_path_value: Path,
            had_configured_pdf_engine: bool,
        ) -> None:
            super().__init__()
            self.profile = profile
            self.input_dir = input_dir
            self.pattern = pattern
            self.recursive = recursive
            self.pandoc_path = pandoc_path_value
            self.history_path = history_path_value
            self.had_configured_pdf_engine = had_configured_pdf_engine

        def run(self) -> None:
            try:
                files = collect_markdown_files(self.input_dir, pattern=self.pattern, recursive=self.recursive)
                if not files:
                    raise RuntimeError(
                        f"No se encontraron archivos con patron '{self.pattern}' en {self.input_dir}"
                    )

                all_results = []
                fallback_warning: str | None = None
                detected_engine: str | None = None
                total = len(files)
                for idx, input_file in enumerate(files):
                    start = int((idx / total) * 90)
                    end = int(((idx + 1) / total) * 90)
                    self.progress.emit(5 + start, f"[{idx + 1}/{total}] Preparando {input_file.name}...")
                    job = ConversionJob(
                        input_path=input_file,
                        outputs=retarget_outputs_for_input(self.profile.outputs, input_file),
                        style_profile=self.profile.style_profile.model_copy(deep=True),
                        metadata=self.profile.metadata.model_copy(deep=True),
                        rules=self.profile.rules.model_copy(deep=True),
                        build_dir=Path("build") / "batch" / input_file.stem,
                    )
                    if not job.metadata.title:
                        job.metadata.title = f"{self.profile.project_name} - {input_file.stem}"

                    try:
                        resolved_pandoc, current_detected = preflight_or_raise(job, self.pandoc_path)
                    except RuntimeError as exc:
                        msg = str(exc)
                        has_html = any(out.format == "html" for out in job.outputs)
                        has_pdf = any(out.format == "pdf" for out in job.outputs)
                        if has_html and has_pdf and "No se detecto motor PDF" in msg:
                            job.outputs = [out for out in job.outputs if out.format != "pdf"]
                            resolved_pandoc = self.pandoc_path
                            current_detected = None
                            fallback_warning = "[warn] motor PDF no disponible; se genero solo HTML en lote."
                        else:
                            raise

                    if current_detected and not detected_engine:
                        detected_engine = current_detected

                    def local_progress(value: int, message: str, s=start, e=end) -> None:
                        mapped = 5 + s + int((value / 100) * max(e - s, 1))
                        self.progress.emit(mapped, f"[{idx + 1}/{total}] {message}")

                    results = run_conversion_job(
                        job,
                        pandoc_path=resolved_pandoc,
                        history_path=self.history_path,
                        progress_callback=local_progress,
                    )
                    all_results.extend(results)
                    self.progress.emit(5 + end, f"[{idx + 1}/{total}] {input_file.name} completado.")

                self.progress.emit(100, "Lote completado.")
                self.finished.emit(
                    {
                        "results": all_results,
                        "detected_engine": detected_engine,
                        "fallback_warning": fallback_warning,
                        "had_configured_pdf_engine": self.had_configured_pdf_engine,
                        "batch_mode": True,
                        "batch_count": total,
                        "pdf_mode": self.profile.style_profile.pdf_layout_mode,
                        "pdf_engine": self.profile.style_profile.pdf_engine,
                    }
                )
            except Exception as exc:  # pragma: no cover
                self.failed.emit(str(exc))

    class StyleCustomizerDialog(QDialog):
        SAMPLE_HTML = """
<h1>Titulo principal</h1>
<p>Texto de ejemplo para revisar alineacion, color y lectura visual.</p>
<h2>Lista</h2>
<ul><li>Elemento uno</li><li>Elemento dos</li><li>Elemento tres</li></ul>
<h2>Tabla</h2>
<table>
  <thead><tr><th>Modulo</th><th>Estado</th><th>Owner</th></tr></thead>
  <tbody>
    <tr><td>Core</td><td>OK</td><td>Ana</td></tr>
    <tr><td>UI</td><td>WIP</td><td>Luis</td></tr>
    <tr><td>QA</td><td>Plan</td><td>Maria</td></tr>
  </tbody>
</table>
<p><a href="#">Enlace de muestra</a></p>
"""
        LIGHT_PALETTES = {
            "title_color": [("#0f172a", "Oscuro"), ("#1d4ed8", "Azul"), ("#7c3aed", "Violeta"), ("#b45309", "Ocre")],
            "text_color": [("#1f2937", "Grafito"), ("#334155", "Slate"), ("#14532d", "Verde"), ("#7f1d1d", "Rojo")],
            "table_header_bg": [("#f8fafc", "Claro"), ("#dbeafe", "Azul"), ("#ecfdf5", "Menta"), ("#fef3c7", "Amarillo")],
            "table_border_color": [("#d1d5db", "Gris"), ("#94a3b8", "Slate"), ("#3b82f6", "Azul"), ("#059669", "Verde")],
            "accent_color": [("#0f766e", "Teal"), ("#2563eb", "Azul"), ("#9333ea", "Violeta"), ("#dc2626", "Rojo")],
        }
        DARK_PALETTES = {
            "title_color": [("#f8fafc", "Claro"), ("#93c5fd", "Azul"), ("#c4b5fd", "Violeta"), ("#fdba74", "Naranja")],
            "text_color": [("#e5e7eb", "Claro"), ("#cbd5e1", "Slate"), ("#bbf7d0", "Menta"), ("#fecaca", "Coral")],
            "table_header_bg": [("#1f2937", "Slate"), ("#1e3a8a", "Azul"), ("#064e3b", "Verde"), ("#78350f", "Ocre")],
            "table_border_color": [("#334155", "Gris"), ("#475569", "Slate"), ("#1d4ed8", "Azul"), ("#0f766e", "Teal")],
            "accent_color": [("#2dd4bf", "Teal"), ("#60a5fa", "Azul"), ("#c084fc", "Violeta"), ("#f87171", "Rojo")],
        }
        THEME_DEFAULTS = {
            "light": {
                "title_color": "#0f172a",
                "text_color": "#1f2937",
                "table_header_bg": "#f8fafc",
                "table_border_color": "#d1d5db",
                "accent_color": "#0f766e",
            },
            "dark": {
                "title_color": "#f8fafc",
                "text_color": "#e5e7eb",
                "table_header_bg": "#1f2937",
                "table_border_color": "#334155",
                "accent_color": "#2dd4bf",
            },
        }
        PRESETS = {
            "Academico Claro": {
                "document_theme": "light",
                "heading_align": "left",
                "text_align": "justify",
                "list_spacing": "normal",
                "table_density": "normal",
                "zebra_tables": True,
                "title_color": "#0f172a",
                "text_color": "#1f2937",
                "accent_color": "#0f766e",
                "table_header_bg": "#f1f5f9",
                "table_border_color": "#cbd5e1",
            },
            "Academico Oscuro": {
                "document_theme": "dark",
                "heading_align": "left",
                "text_align": "left",
                "list_spacing": "normal",
                "table_density": "normal",
                "zebra_tables": True,
                "title_color": "#f8fafc",
                "text_color": "#e5e7eb",
                "accent_color": "#2dd4bf",
                "table_header_bg": "#1f2937",
                "table_border_color": "#334155",
            },
            "Corporativo": {
                "document_theme": "light",
                "heading_align": "left",
                "text_align": "left",
                "list_spacing": "compact",
                "table_density": "compact",
                "zebra_tables": False,
                "title_color": "#0b172a",
                "text_color": "#1f2937",
                "accent_color": "#1d4ed8",
                "table_header_bg": "#dbeafe",
                "table_border_color": "#93c5fd",
            },
            "UE Audit": {
                "document_theme": "dark",
                "heading_align": "left",
                "text_align": "left",
                "list_spacing": "normal",
                "table_density": "normal",
                "zebra_tables": True,
                "title_color": "#93c5fd",
                "text_color": "#e5e7eb",
                "accent_color": "#22d3ee",
                "table_header_bg": "#1e293b",
                "table_border_color": "#334155",
            },
            "UE Architecture": {
                "document_theme": "light",
                "heading_align": "left",
                "text_align": "justify",
                "list_spacing": "normal",
                "table_density": "normal",
                "zebra_tables": True,
                "title_color": "#0f172a",
                "text_color": "#1f2937",
                "accent_color": "#0ea5e9",
                "table_header_bg": "#e0f2fe",
                "table_border_color": "#7dd3fc",
            },
        }

        def __init__(self, options: StyleOptions, parent: QWidget | None = None) -> None:
            super().__init__(parent)
            self.setWindowTitle("Dashboard de Personalizacion")
            self.resize(980, 620)
            self.options = options.model_copy(deep=True)

            root = QHBoxLayout(self)
            controls = QVBoxLayout()
            controls.setSpacing(8)
            preview_wrap = QVBoxLayout()

            controls.addWidget(QLabel("Presets rapidos"))
            controls.addLayout(
                self._make_preset_buttons(
                    list(self.PRESETS.keys()),
                )
            )
            controls.addWidget(QLabel("Alineacion de titulos"))
            controls.addLayout(
                self._make_choice_buttons(
                    [("Izquierda", "left"), ("Centro", "center"), ("Derecha", "right")],
                    self.options.heading_align,
                    lambda value: self._set_attr("heading_align", value),
                )
            )
            controls.addWidget(QLabel("Alineacion de texto"))
            controls.addLayout(
                self._make_choice_buttons(
                    [("Izquierda", "left"), ("Justificado", "justify")],
                    self.options.text_align,
                    lambda value: self._set_attr("text_align", value),
                )
            )
            controls.addWidget(QLabel("Espaciado de listas"))
            controls.addLayout(
                self._make_choice_buttons(
                    [("Compacto", "compact"), ("Normal", "normal"), ("Amplio", "spacious")],
                    self.options.list_spacing,
                    lambda value: self._set_attr("list_spacing", value),
                )
            )
            controls.addWidget(QLabel("Densidad de tablas"))
            controls.addLayout(
                self._make_choice_buttons(
                    [("Compacta", "compact"), ("Normal", "normal"), ("Amplia", "spacious")],
                    self.options.table_density,
                    lambda value: self._set_attr("table_density", value),
                )
            )

            self.zebra_check = QCheckBox("Tabla cebra")
            self.zebra_check.setChecked(self.options.zebra_tables)
            self.zebra_check.toggled.connect(lambda checked: self._set_attr("zebra_tables", checked))
            controls.addWidget(self.zebra_check)

            controls.addWidget(QLabel("Tema del documento"))
            controls.addLayout(
                self._make_choice_buttons(
                    [("Claro", "light"), ("Oscuro", "dark")],
                    self.options.document_theme,
                    self._set_document_theme,
                )
            )

            controls.addWidget(QLabel("Color de titulos"))
            self.title_color_row = QHBoxLayout()
            controls.addLayout(self.title_color_row)
            controls.addWidget(QLabel("Color de texto"))
            self.text_color_row = QHBoxLayout()
            controls.addLayout(self.text_color_row)
            controls.addWidget(QLabel("Color encabezado tabla"))
            self.table_header_row = QHBoxLayout()
            controls.addLayout(self.table_header_row)
            controls.addWidget(QLabel("Color borde tabla"))
            self.table_border_row = QHBoxLayout()
            controls.addLayout(self.table_border_row)
            controls.addWidget(QLabel("Color enlaces/acento"))
            self.accent_row = QHBoxLayout()
            controls.addLayout(self.accent_row)
            controls.addStretch()

            self.preview = QTextBrowser()
            self.preview.setOpenExternalLinks(True)
            preview_wrap.addWidget(QLabel("Vista previa en tiempo real"))
            preview_wrap.addWidget(self.preview)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            preview_wrap.addWidget(buttons)

            root.addLayout(controls, 3)
            root.addLayout(preview_wrap, 4)
            self._rebuild_color_rows()
            self._refresh_preview()

        def _set_attr(self, attr: str, value: str | bool) -> None:
            setattr(self.options, attr, value)
            self._refresh_preview()

        def _make_choice_buttons(
            self, choices: list[tuple[str, str]], current: str, on_change
        ) -> QHBoxLayout:
            row = QHBoxLayout()
            group = QButtonGroup(self)
            group.setExclusive(True)
            for label, value in choices:
                btn = QPushButton(label)
                btn.setObjectName("ChoiceButton")
                btn.setCheckable(True)
                btn.setChecked(value == current)
                btn.clicked.connect(lambda checked=False, v=value: on_change(v))
                row.addWidget(btn)
                group.addButton(btn)
            return row

        def _make_preset_buttons(self, names: list[str]) -> QHBoxLayout:
            row = QHBoxLayout()
            for name in names:
                btn = QPushButton(name)
                btn.clicked.connect(lambda checked=False, preset=name: self._apply_preset(preset))
                row.addWidget(btn)
            return row

        def _apply_preset(self, preset_name: str) -> None:
            payload = self.PRESETS.get(preset_name)
            if not payload:
                return
            self.options = StyleOptions.model_validate(payload)
            self.zebra_check.setChecked(self.options.zebra_tables)
            self._rebuild_color_rows()
            self._refresh_preview()

        def _set_document_theme(self, theme: str) -> None:
            self.options.document_theme = theme  # type: ignore[assignment]
            defaults = self.THEME_DEFAULTS[theme]
            self.options.title_color = defaults["title_color"]
            self.options.text_color = defaults["text_color"]
            self.options.table_header_bg = defaults["table_header_bg"]
            self.options.table_border_color = defaults["table_border_color"]
            self.options.accent_color = defaults["accent_color"]
            self._rebuild_color_rows()
            self._refresh_preview()

        def _palette_map(self) -> dict[str, list[tuple[str, str]]]:
            return self.DARK_PALETTES if self.options.document_theme == "dark" else self.LIGHT_PALETTES

        @staticmethod
        def _clear_row(row: QHBoxLayout) -> None:
            while row.count():
                item = row.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        @staticmethod
        def _label_color_for_bg(hex_color: str) -> str:
            c = hex_color.lstrip("#")
            if len(c) != 6:
                return "#f8fafc"
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            luminance = (0.299 * r) + (0.587 * g) + (0.114 * b)
            return "#0f172a" if luminance > 160 else "#f8fafc"

        def _fill_color_row(self, row: QHBoxLayout, field: str, current: str) -> None:
            self._clear_row(row)
            choices = self._palette_map()[field]
            group = QButtonGroup(self)
            group.setExclusive(True)
            for hex_color, label in choices:
                text_color = self._label_color_for_bg(hex_color)
                btn = QPushButton(label)
                btn.setObjectName("ColorSwatch")
                btn.setCheckable(True)
                btn.setChecked(hex_color.lower() == current.lower())
                btn.setStyleSheet(
                    f"QPushButton#ColorSwatch {{ border: 1px solid #64748b; border-radius: 6px; padding: 6px; background:{hex_color}; color:{text_color}; }}"
                    "QPushButton#ColorSwatch:hover { border: 2px solid #e2e8f0; }"
                    "QPushButton#ColorSwatch:pressed { border: 2px solid #38bdf8; }"
                    "QPushButton#ColorSwatch:checked { border: 3px solid #38bdf8; }"
                )
                btn.clicked.connect(lambda checked=False, v=hex_color, f=field: self._set_attr(f, v))
                row.addWidget(btn)  # type: ignore[arg-type]
                group.addButton(btn)
            row.addStretch()

        def _rebuild_color_rows(self) -> None:
            self._fill_color_row(self.title_color_row, "title_color", self.options.title_color)
            self._fill_color_row(self.text_color_row, "text_color", self.options.text_color)
            self._fill_color_row(self.table_header_row, "table_header_bg", self.options.table_header_bg)
            self._fill_color_row(self.table_border_row, "table_border_color", self.options.table_border_color)
            self._fill_color_row(self.accent_row, "accent_color", self.options.accent_color)

        def _refresh_preview(self) -> None:
            css = build_override_css(self.options)
            html = f"<html><head><style>{css}</style></head><body>{self.SAMPLE_HTML}</body></html>"
            self.preview.setHtml(html)

        def get_options(self) -> StyleOptions:
            return self.options.model_copy(deep=True)

    class MainWindow(QMainWindow):
        DOCUMENT_PRESETS = {
            "Draft": {
                "classification": "internal",
                "watermark": "DRAFT",
                "signatures_enabled": False,
                "footer_left": "Draft",
                "footer_center": "",
                "footer_right": "Pagina {page}/{total}",
            },
            "Internal": {
                "classification": "internal",
                "watermark": "",
                "signatures_enabled": True,
                "footer_left": "Internal",
                "footer_center": "",
                "footer_right": "Pagina {page}/{total}",
            },
            "Approved": {
                "classification": "public",
                "watermark": "",
                "signatures_enabled": True,
                "footer_left": "Approved",
                "footer_center": "",
                "footer_right": "Pagina {page}/{total}",
            },
            "Confidential": {
                "classification": "confidential",
                "watermark": "CONFIDENTIAL",
                "signatures_enabled": True,
                "footer_left": "Confidential",
                "footer_center": "",
                "footer_right": "Pagina {page}/{total}",
            },
            "UE Audit Internal": {
                "classification": "internal",
                "watermark": "",
                "signatures_enabled": True,
                "footer_left": "UE Internal",
                "footer_center": "",
                "footer_right": "Page {page}/{total}",
            },
            "UE Architecture Public": {
                "classification": "public",
                "watermark": "",
                "signatures_enabled": False,
                "footer_left": "UE Architecture",
                "footer_center": "",
                "footer_right": "Page {page}/{total}",
            },
        }

        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("DocsConverter Dashboard")
            self.resize(1300, 820)
            self.history_path = Path("logs/history.jsonl")
            self._last_html_output: Path | None = None
            self._last_pdf_output: Path | None = None
            self._last_docx_output: Path | None = None
            self._last_epub_output: Path | None = None
            self._last_batch_summary_text: str | None = None
            self._last_batch_summary_json: dict | None = None
            self._last_batch_summary_rows: list[dict[str, str | int]] = []
            self._last_run_pdf_requested = False
            self._last_run_pdf_failed = False
            self._pandoc_path = pandoc_path
            self._style_options = StyleOptions()
            self._conversion_thread: QThread | None = None
            self._conversion_worker: ConversionWorker | None = None
            self._progress_dialog: QProgressDialog | None = None
            self._apply_styles()

            root = QWidget()
            shell = QHBoxLayout(root)
            shell.setContentsMargins(10, 10, 10, 10)
            shell.setSpacing(10)

            nav = self._build_nav()
            self.pages = QStackedWidget()
            self.pages.addWidget(self._build_dashboard_page())
            self.pages.addWidget(self._build_converter_page())
            self.pages.addWidget(self._build_history_page())
            self.pages.addWidget(self._build_settings_page())
            self.pages.addWidget(self._build_sanitization_page())  # Nueva página

            split = QSplitter(Qt.Orientation.Horizontal)
            split.addWidget(nav)
            split.addWidget(self.pages)
            split.setSizes([260, 1000])
            shell.addWidget(split)

            self.setCentralWidget(root)
            self.load_profile_to_form()
            self.refresh_history()
            self.refresh_dashboard_metrics()

        def _apply_styles(self) -> None:
            self.setStyleSheet(
                """
                QWidget { background: #0b1220; color: #e5e7eb; font-size: 13px; }
                QFrame#Card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; }
                QLabel#Title { font-size: 20px; font-weight: 700; color: #f8fafc; }
                QLabel#MetricValue { font-size: 26px; font-weight: 700; color: #f8fafc; }
                QLabel#MetricLabel { font-size: 12px; color: #94a3b8; }

                QPushButton {
                  background: #1f2937;
                  color: #e5e7eb;
                  border: 1px solid #334155;
                  border-radius: 8px;
                  padding: 8px 12px;
                }
                QPushButton:hover { background: #253347; border-color: #60a5fa; }
                QPushButton:pressed { background: #1e293b; border-color: #3b82f6; }
                QPushButton:checked { background: #0f3a5f; border: 2px solid #60a5fa; color: #f8fafc; }
                QPushButton#ChoiceButton { min-height: 30px; }

                QPushButton#NavButton { text-align: left; padding: 10px; }
                QPushButton#ActionButton { 
                  background: #10b981; 
                  color: #064e3b; 
                  border: 1px solid #34d399;
                  font-weight: 700;
                  text-align: center;
                }
                QPushButton#ActionButton:hover { background: #34d399; }
                QPushButton#ActionButton:pressed { background: #059669; color: #d1fae5; }
                QPushButton#Primary {
                  background: #0ea5e9;
                  color: #062132;
                  border: 1px solid #38bdf8;
                  font-weight: 700;
                }
                QPushButton#Primary:hover { background: #38bdf8; }
                QPushButton#Primary:pressed { background: #0284c7; color: #e0f2fe; }

                QLineEdit, QTextEdit, QTextBrowser, QTableWidget {
                  background: #0f172a;
                  border: 1px solid #334155;
                  border-radius: 6px;
                  padding: 6px;
                  color: #e5e7eb;
                }
                QHeaderView::section {
                  background: #1f2937;
                  color: #e5e7eb;
                  border: 1px solid #334155;
                  padding: 6px;
                }
                QTabBar::tab {
                  background: #111827;
                  color: #cbd5e1;
                  border: 1px solid #334155;
                  padding: 6px 10px;
                }
                QTabBar::tab:selected {
                  background: #1e293b;
                  color: #f8fafc;
                  border-bottom: 2px solid #38bdf8;
                }
                """
            )

        def _build_nav(self) -> QWidget:
            nav = QFrame()
            nav.setObjectName("Card")
            layout = QVBoxLayout(nav)
            layout.setContentsMargins(14, 14, 14, 14)
            layout.setSpacing(8)

            title = QLabel("DocsConverter")
            title.setObjectName("Title")
            subtitle = QLabel("Dashboard UX")
            subtitle.setObjectName("MetricLabel")
            layout.addWidget(title)
            layout.addWidget(subtitle)

            for text, idx in [("Resumen", 0), ("Convertidor", 1), ("Historial", 2), ("Configuracion", 3)]:
                btn = QPushButton(text)
                btn.setObjectName("NavButton")
                btn.clicked.connect(lambda checked=False, page_idx=idx: self.pages.setCurrentIndex(page_idx))
                layout.addWidget(btn)
            
            # Separador visual
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setStyleSheet("background-color: #374151; margin: 10px 0;")
            layout.addWidget(separator)
            
            # Botón Sanitización
            btn_sanitize = QPushButton("🧹 Sanitización")
            btn_sanitize.setObjectName("NavButton")
            btn_sanitize.setToolTip("Limpiar y validar markdown antes de convertir")
            btn_sanitize.clicked.connect(lambda: self.pages.setCurrentIndex(4))  # Nueva página
            layout.addWidget(btn_sanitize)
            
            # Botón Convertir rápido
            btn_quick_convert = QPushButton("⚡ Convertir")
            btn_quick_convert.setObjectName("ActionButton")
            btn_quick_convert.setToolTip("Convertir sin hacer scroll")
            btn_quick_convert.clicked.connect(self._quick_convert)
            layout.addWidget(btn_quick_convert)

            layout.addStretch()
            return nav

        def _metric_card(self, label: str) -> tuple[QFrame, QLabel]:
            card = QFrame()
            card.setObjectName("Card")
            box = QVBoxLayout(card)
            value = QLabel("0")
            value.setObjectName("MetricValue")
            text = QLabel(label)
            text.setObjectName("MetricLabel")
            box.addWidget(value)
            box.addWidget(text)
            return card, value

        def _build_dashboard_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setSpacing(10)
            header = QLabel("Resumen Operativo")
            header.setObjectName("Title")
            layout.addWidget(header)
            row = QHBoxLayout()
            card_total, self.metric_total = self._metric_card("Conversiones registradas")
            card_ok, self.metric_ok = self._metric_card("Conversiones exitosas")
            card_err, self.metric_err = self._metric_card("Conversiones con error")
            row.addWidget(card_total)
            row.addWidget(card_ok)
            row.addWidget(card_err)
            layout.addLayout(row)
            layout.addWidget(QLabel("Usa Convertidor para ejecutar trabajos y validar resultados."))
            layout.addStretch()
            return page

        def _build_converter_page(self) -> QWidget:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            container = QWidget()
            layout = QVBoxLayout(container)
            row_input = QHBoxLayout()
            self.input_edit = QLineEdit("samples/markdown/basic-report.md")
            btn_input = QPushButton("Archivo MD")
            btn_input.clicked.connect(self.select_input)
            row_input.addWidget(QLabel("Input"))
            row_input.addWidget(self.input_edit)
            row_input.addWidget(btn_input)

            row_batch = QHBoxLayout()
            self.batch_dir_edit = QLineEdit("samples/markdown")
            btn_batch_dir = QPushButton("Carpeta lote")
            btn_batch_dir.clicked.connect(self.select_batch_dir)
            self.batch_pattern_edit = QLineEdit("*.md")
            self.batch_recursive_check = QCheckBox("Recursivo")
            self.batch_recursive_check.setChecked(True)
            row_batch.addWidget(QLabel("Batch"))
            row_batch.addWidget(self.batch_dir_edit)
            row_batch.addWidget(btn_batch_dir)
            row_batch.addWidget(QLabel("Patron"))
            row_batch.addWidget(self.batch_pattern_edit)
            row_batch.addWidget(self.batch_recursive_check)

            row_profile = QHBoxLayout()
            self.profile_edit = QLineEdit("configs/profiles/default.yaml")
            btn_profile = QPushButton("Perfil")
            btn_profile.clicked.connect(self.select_profile)
            btn_load = QPushButton("Cargar")
            btn_load.clicked.connect(self.load_profile_to_form)
            btn_save = QPushButton("Guardar")
            btn_save.clicked.connect(self.save_profile_from_form)
            row_profile.addWidget(QLabel("Perfil"))
            row_profile.addWidget(self.profile_edit)
            row_profile.addWidget(btn_profile)
            row_profile.addWidget(btn_load)
            row_profile.addWidget(btn_save)

            form = QFormLayout()
            self.project_name_edit = QLineEdit("Reporte Default")
            self.meta_title_edit = QLineEdit("Reporte Default")
            self.meta_subtitle_edit = QLineEdit("")
            self.meta_author_edit = QLineEdit("")
            self.meta_reviewer_edit = QLineEdit("")
            self.meta_version_edit = QLineEdit("1.0")
            self.meta_classification_combo = QComboBox()
            self.meta_classification_combo.addItems(["internal", "confidential", "public"])
            self.meta_language_combo = QComboBox()
            self.meta_language_combo.addItems(["es", "en"])
            self.meta_date_edit = QLineEdit("")
            self.meta_header_left_edit = QLineEdit("")
            self.meta_header_center_edit = QLineEdit("")
            self.meta_header_right_edit = QLineEdit("")
            self.meta_footer_left_edit = QLineEdit("")
            self.meta_footer_center_edit = QLineEdit("")
            self.meta_footer_right_edit = QLineEdit("")
            self.meta_watermark_edit = QLineEdit("")
            self.meta_approver_edit = QLineEdit("")
            self.meta_approval_date_edit = QLineEdit("")
            self.meta_signatures_check = QCheckBox()
            self.doc_preset_combo = QComboBox()
            self.doc_preset_combo.addItem("Sin preset")
            for preset_name in self.DOCUMENT_PRESETS.keys():
                self.doc_preset_combo.addItem(preset_name)
            self.output_html_check = QCheckBox()
            self.output_html_check.setChecked(True)
            self.output_html_edit = QLineEdit("build/output/report.html")
            self.output_pdf_check = QCheckBox()
            self.output_pdf_check.setChecked(True)
            self.output_pdf_edit = QLineEdit("build/output/report.pdf")
            self.output_docx_check = QCheckBox()
            self.output_docx_check.setChecked(False)
            self.output_docx_edit = QLineEdit("build/output/report.docx")
            self.output_epub_check = QCheckBox()
            self.output_epub_check.setChecked(False)
            self.output_epub_edit = QLineEdit("build/output/report.epub")
            self.pdf_engine_edit = QLineEdit("")
            self.pdf_layout_mode_combo = QComboBox()
            self.pdf_layout_mode_combo.addItems(["web", "native"])
            self.pdf_layout_mode_combo.currentTextChanged.connect(self.on_pdf_mode_changed)
            self.template_html_edit = QLineEdit("templates/base.html")
            self.template_pdf_edit = QLineEdit("")
            self.css_edit = QLineEdit("styles/report.css")

            template_row = QHBoxLayout()
            template_row.addWidget(self.template_html_edit)
            btn_template = QPushButton("Template")
            btn_template.clicked.connect(self.select_template)
            template_row.addWidget(btn_template)

            template_pdf_row = QHBoxLayout()
            template_pdf_row.addWidget(self.template_pdf_edit)
            btn_template_pdf = QPushButton("Template PDF")
            btn_template_pdf.clicked.connect(self.select_template_pdf)
            template_pdf_row.addWidget(btn_template_pdf)

            css_row = QHBoxLayout()
            css_row.addWidget(self.css_edit)
            btn_css = QPushButton("CSS")
            btn_css.clicked.connect(self.select_css)
            css_row.addWidget(btn_css)

            self.rule_heading_check = QCheckBox()
            self.rule_heading_check.setChecked(True)
            self.rule_fences_check = QCheckBox()
            self.rule_fences_check.setChecked(True)
            self.rule_links_check = QCheckBox()

            style_row = QHBoxLayout()
            btn_customize = QPushButton("Abrir dashboard de personalizacion")
            btn_customize.clicked.connect(self.open_style_customizer)
            self.style_summary = QLabel("")
            self.style_summary.setObjectName("MetricLabel")
            style_row.addWidget(btn_customize)
            style_row.addWidget(self.style_summary)

            preset_row = QHBoxLayout()
            self.preset_combo = QComboBox()
            self.preset_combo.addItem("Sin preset")
            for preset_name in StyleCustomizerDialog.PRESETS.keys():
                self.preset_combo.addItem(preset_name)
            btn_apply_preset = QPushButton("Aplicar preset")
            btn_apply_preset.clicked.connect(self.apply_selected_preset)
            preset_row.addWidget(self.preset_combo)
            preset_row.addWidget(btn_apply_preset)
            preset_row.addStretch()

            form.addRow("Proyecto", self.project_name_edit)
            form.addRow("Titulo", self.meta_title_edit)
            form.addRow("Subtitulo", self.meta_subtitle_edit)
            form.addRow("Autor", self.meta_author_edit)
            form.addRow("Revisor", self.meta_reviewer_edit)
            form.addRow("Version", self.meta_version_edit)
            form.addRow("Clasificacion", self.meta_classification_combo)
            form.addRow("Idioma", self.meta_language_combo)
            form.addRow("Fecha", self.meta_date_edit)
            form.addRow("Header izq", self.meta_header_left_edit)
            form.addRow("Header centro", self.meta_header_center_edit)
            form.addRow("Header der", self.meta_header_right_edit)
            form.addRow("Footer izq", self.meta_footer_left_edit)
            form.addRow("Footer centro", self.meta_footer_center_edit)
            form.addRow("Footer der", self.meta_footer_right_edit)
            form.addRow("Watermark", self.meta_watermark_edit)
            form.addRow("Aprobador", self.meta_approver_edit)
            form.addRow("Fecha aprobacion", self.meta_approval_date_edit)
            form.addRow("Bloque firmas", self.meta_signatures_check)
            doc_preset_row = QHBoxLayout()
            doc_preset_row.addWidget(self.doc_preset_combo)
            btn_apply_doc_preset = QPushButton("Aplicar preset documental")
            btn_apply_doc_preset.clicked.connect(self.apply_document_preset)
            doc_preset_row.addWidget(btn_apply_doc_preset)
            doc_preset_row.addStretch()
            form.addRow("Preset documental", doc_preset_row)
            form.addRow("Exportar HTML", self.output_html_check)
            form.addRow("Ruta HTML", self.output_html_edit)
            form.addRow("Exportar PDF", self.output_pdf_check)
            form.addRow("Ruta PDF", self.output_pdf_edit)
            form.addRow("Exportar DOCX", self.output_docx_check)
            form.addRow("Ruta DOCX", self.output_docx_edit)
            form.addRow("Exportar EPUB", self.output_epub_check)
            form.addRow("Ruta EPUB", self.output_epub_edit)
            form.addRow("Motor PDF", self.pdf_engine_edit)
            form.addRow("Modo PDF", self.pdf_layout_mode_combo)
            form.addRow("Template HTML", template_row)
            form.addRow("Template PDF", template_pdf_row)
            form.addRow("Estilo CSS", css_row)
            form.addRow("Personalizacion", style_row)
            form.addRow("Preset visual", preset_row)
            form.addRow("normalize_headings", self.rule_heading_check)
            form.addRow("fix_code_fences", self.rule_fences_check)
            form.addRow("sanitize_links", self.rule_links_check)

            action_row = QHBoxLayout()
            self.btn_convert = QPushButton("Convertir")
            self.btn_convert.setObjectName("Primary")
            self.btn_convert.clicked.connect(self.convert)
            self.btn_convert_batch = QPushButton("Convertir carpeta (lote)")
            self.btn_convert_batch.clicked.connect(self.convert_batch)
            btn_open_html = QPushButton("Abrir ultimo HTML")
            btn_open_html.clicked.connect(self.open_last_html)
            btn_open_pdf = QPushButton("Abrir ultimo PDF")
            btn_open_pdf.clicked.connect(self.open_last_pdf)
            btn_open_docx = QPushButton("Abrir ultimo DOCX")
            btn_open_docx.clicked.connect(self.open_last_docx)
            btn_open_epub = QPushButton("Abrir ultimo EPUB")
            btn_open_epub.clicked.connect(self.open_last_epub)
            btn_export_batch = QPushButton("Exportar resumen lote")
            btn_export_batch.clicked.connect(self.export_batch_summary)
            action_row.addWidget(self.btn_convert)
            action_row.addWidget(self.btn_convert_batch)
            action_row.addWidget(btn_open_html)
            action_row.addWidget(btn_open_pdf)
            action_row.addWidget(btn_open_docx)
            action_row.addWidget(btn_open_epub)
            action_row.addWidget(btn_export_batch)
            action_row.addStretch()

            self.log = QTextEdit()
            self.log.setReadOnly(True)
            self.preview = QTextBrowser()
            self.preview.setOpenExternalLinks(True)
            self.batch_summary_table = QTableWidget(0, 5)
            self.batch_summary_table.setHorizontalHeaderLabels(
                ["Archivo", "Formato", "Estado", "Codigo", "Salida"]
            )
            self.batch_summary_table.horizontalHeader().setStretchLastSection(True)
            tabs = QTabWidget()
            tabs.addTab(self.log, "Logs")
            tabs.addTab(self.preview, "Vista previa HTML")
            tabs.addTab(self.batch_summary_table, "Resumen lote")

            layout.addLayout(row_input)
            layout.addLayout(row_batch)
            layout.addLayout(row_profile)
            layout.addLayout(form)
            layout.addLayout(action_row)
            layout.addWidget(tabs)
            layout.addStretch()
            scroll.setWidget(container)
            page_layout.addWidget(scroll)
            return page

        def _build_history_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            top = QHBoxLayout()
            title = QLabel("Historial de conversiones")
            title.setObjectName("Title")
            btn_refresh = QPushButton("Refrescar")
            btn_refresh.clicked.connect(self.refresh_history)
            top.addWidget(title)
            top.addStretch()
            top.addWidget(btn_refresh)
            self.history_table = QTableWidget(0, 4)
            self.history_table.setHorizontalHeaderLabels(["Fecha", "Formato", "Codigo", "Salida"])
            self.history_table.horizontalHeader().setStretchLastSection(True)
            layout.addLayout(top)
            layout.addWidget(self.history_table)
            return page

        def _build_settings_page(self) -> QWidget:
            page = QWidget()
            layout = QVBoxLayout(page)
            title = QLabel("Configuracion")
            title.setObjectName("Title")
            layout.addWidget(title)
            card = QFrame()
            card.setObjectName("Card")
            form = QFormLayout(card)
            self.pandoc_edit = QLineEdit(str(self._pandoc_path))
            form.addRow("Ruta Pandoc", self.pandoc_edit)
            form.addRow("Nota", QLabel("Se usa en el siguiente preflight/conversion."))
            btn_apply = QPushButton("Aplicar")
            btn_apply.setObjectName("Primary")
            btn_apply.clicked.connect(self.apply_settings)
            layout.addWidget(card)
            layout.addWidget(btn_apply)
            layout.addStretch()
            return page
        
        def _build_sanitization_page(self) -> QWidget:
            """Panel de sanitización de markdown."""
            page = QWidget()
            layout = QVBoxLayout(page)
            
            # Título
            title = QLabel("🧹 Sanitización de Markdown")
            title.setObjectName("Title")
            layout.addWidget(title)
            
            # Card principal
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            
            # Descripción
            desc = QLabel(
                "Limpia el markdown eliminando marcadores, comentarios y elementos no deseados "
                "antes de convertir. Las reglas se configuran en configs/sanitization.yaml"
            )
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #9ca3af; margin-bottom: 15px;")
            card_layout.addWidget(desc)
            
            # Estado del archivo cargado
            status_layout = QHBoxLayout()
            status_label = QLabel("📄 Archivo:")
            self.sanitize_file_label = QLabel("Ninguno cargado")
            self.sanitize_file_label.setStyleSheet("color: #6b7280;")
            status_layout.addWidget(status_label)
            status_layout.addWidget(self.sanitize_file_label)
            status_layout.addStretch()
            card_layout.addLayout(status_layout)
            
            # Botones de acción
            btn_layout = QHBoxLayout()
            
            btn_load_config = QPushButton("📋 Cargar Config")
            btn_load_config.setToolTip("Cargar configs/sanitization.yaml")
            btn_load_config.clicked.connect(self._load_sanitization_config)
            
            btn_preview = QPushButton("👁️ Vista Previa")
            btn_preview.setToolTip("Ver qué se eliminará sin aplicar cambios")
            btn_preview.clicked.connect(self._preview_sanitization)
            
            btn_apply = QPushButton("✨ Limpiar y Convertir")
            btn_apply.setObjectName("Primary")
            btn_apply.setToolTip("Sanitizar markdown y luego convertir")
            btn_apply.clicked.connect(self._sanitize_and_convert)
            
            btn_layout.addWidget(btn_load_config)
            btn_layout.addWidget(btn_preview)
            btn_layout.addStretch()
            btn_layout.addWidget(btn_apply)
            
            card_layout.addLayout(btn_layout)
            
            # Área de reglas activas
            rules_label = QLabel("Reglas activas:")
            rules_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
            card_layout.addWidget(rules_label)
            
            self.sanitize_rules_text = QTextBrowser()
            self.sanitize_rules_text.setMaximumHeight(200)
            self.sanitize_rules_text.setStyleSheet(
                "background-color: #1f2937; border: 1px solid #374151; "
                "border-radius: 4px; padding: 10px; color: #d1d5db;"
            )
            self.sanitize_rules_text.setPlainText("Carga la configuración para ver las reglas...")
            card_layout.addWidget(self.sanitize_rules_text)
            
            # Log de sanitización
            log_label = QLabel("Resultado de sanitización:")
            log_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
            card_layout.addWidget(log_label)
            
            self.sanitize_log = QTextBrowser()
            self.sanitize_log.setStyleSheet(
                "background-color: #111827; border: 1px solid #374151; "
                "border-radius: 4px; padding: 10px; font-family: 'Consolas', monospace; "
                "color: #10b981;"
            )
            card_layout.addWidget(self.sanitize_log)
            
            layout.addWidget(card)
            layout.addStretch()
            
            # Inicializar configuración de sanitización
            self._sanitization_config = None
            
            return page

        def _load_sanitization_config(self) -> None:
            """Carga la configuración de sanitización desde YAML."""
            try:
                from app.core.sanitizer_config import load_sanitization_config
                config_path = Path("configs/sanitization.yaml")
                
                if not config_path.exists():
                    self.sanitize_log.append("⚠️  configs/sanitization.yaml no encontrado")
                    self.sanitize_log.append("   Creando configuración por defecto...")
                    # Crear configuración por defecto
                    from app.core.sanitizer import SanitizationConfig
                    self._sanitization_config = SanitizationConfig()
                else:
                    self._sanitization_config = load_sanitization_config(config_path)
                    self.sanitize_log.append(f"✅ Configuración cargada: {len(self._sanitization_config.rules)} reglas")
                
                # Mostrar reglas activas
                active_rules = [r for r in self._sanitization_config.rules if r.enabled]
                rules_text = f"Total: {len(self._sanitization_config.rules)} reglas ({len(active_rules)} activas)\n\n"
                
                for i, rule in enumerate(active_rules, 1):
                    status = "✅" if rule.enabled else "⏸️"
                    rules_text += f"{status} {i}. {rule.name}\n"
                    rules_text += f"   Acción: {rule.action}, Scope: {rule.scope}\n"
                    rules_text += f"   Patrón: {rule.pattern[:60]}...\n\n"
                
                self.sanitize_rules_text.setPlainText(rules_text)
                
            except Exception as e:
                self.sanitize_log.append(f"❌ Error cargando configuración: {str(e)}")
        
        def _preview_sanitization(self) -> None:
            """Muestra una vista previa de lo que se sanitizará."""
            if not self.input_file_edit.text():
                QMessageBox.warning(self, "Advertencia", "Primero carga un archivo en la pestaña Convertidor")
                return
            
            if not self._sanitization_config:
                self._load_sanitization_config()
            
            try:
                from app.core.sanitizer import MarkdownSanitizer
                
                input_path = Path(self.input_file_edit.text())
                content = input_path.read_text(encoding="utf-8")
                
                sanitizer = MarkdownSanitizer(self._sanitization_config)
                cleaned, stats = sanitizer.sanitize(content)
                
                self.sanitize_log.clear()
                self.sanitize_log.append("📊 Vista previa de sanitización:")
                self.sanitize_log.append(f"   • Líneas eliminadas: {stats['lines_removed']}")
                self.sanitize_log.append(f"   • Matches eliminados: {stats['matches_removed']}")
                self.sanitize_log.append(f"   • Reemplazos hechos: {stats['replacements_made']}")
                self.sanitize_log.append("")
                self.sanitize_log.append("✅ Parece correcto - usa 'Limpiar y Convertir' para aplicar")
                
            except Exception as e:
                self.sanitize_log.append(f"❌ Error en vista previa: {str(e)}")
        
        def _sanitize_and_convert(self) -> None:
            """Sanitiza el markdown y luego lo convierte."""
            if not self._sanitization_config:
                self._load_sanitization_config()
            
            # Guardar config temporalmente para que el pipeline la use
            self._temp_sanitization_config = self._sanitization_config
            
            # Ejecutar conversión normal (el pipeline ya lo maneja)
            self.log.append("[sanitize] Aplicando reglas de sanitización...")
            self._quick_convert()
        
        def _quick_convert(self) -> None:
            """Acceso rápido al botón de conversión sin hacer scroll."""
            # Cambiar a la página de convertidor
            self.pages.setCurrentIndex(1)
            # Simular click en el botón de conversión
            self._run_single_conversion()

        def _refresh_style_summary(self) -> None:
            opt = self._style_options
            self.style_summary.setText(
                f"tema:{opt.document_theme} titulos:{opt.heading_align} texto:{opt.text_align} listas:{opt.list_spacing} tablas:{opt.table_density} acento:{opt.accent_color}"
            )

        def open_style_customizer(self) -> None:
            dialog = StyleCustomizerDialog(self._style_options, self)
            if dialog.exec():
                self._style_options = dialog.get_options()
                self._refresh_style_summary()

        def apply_selected_preset(self) -> None:
            selected = self.preset_combo.currentText().strip()
            if not selected or selected == "Sin preset":
                return
            payload = StyleCustomizerDialog.PRESETS.get(selected)
            if not payload:
                return
            self._style_options = StyleOptions.model_validate(payload)
            self._refresh_style_summary()
            self.log.append(f"[ok] preset aplicado: {selected}")

        def apply_document_preset(self) -> None:
            selected = self.doc_preset_combo.currentText().strip()
            if not selected or selected == "Sin preset":
                return
            payload = self.DOCUMENT_PRESETS.get(selected)
            if not payload:
                return
            self.meta_classification_combo.setCurrentText(payload["classification"])
            self.meta_watermark_edit.setText(payload["watermark"])
            self.meta_signatures_check.setChecked(bool(payload["signatures_enabled"]))
            self.meta_footer_left_edit.setText(payload["footer_left"])
            self.meta_footer_center_edit.setText(payload["footer_center"])
            self.meta_footer_right_edit.setText(payload["footer_right"])
            if not self.meta_header_left_edit.text().strip():
                self.meta_header_left_edit.setText("DocsConverter")
            if not self.meta_header_center_edit.text().strip():
                self.meta_header_center_edit.setText(self.project_name_edit.text().strip() or "Reporte")
            if not self.meta_header_right_edit.text().strip():
                self.meta_header_right_edit.setText(self.meta_version_edit.text().strip() or "v1.0")
            if selected.startswith("UE "):
                self.meta_language_combo.setCurrentText("en")
                self.meta_header_left_edit.setText("Unreal Engine")
                self.meta_header_center_edit.setText(self.project_name_edit.text().strip() or "UE Report")
                self.meta_header_right_edit.setText(self.meta_version_edit.text().strip() or "v1.0")
            if selected in {"Approved", "Confidential"} and not self.meta_approval_date_edit.text().strip():
                self.meta_approval_date_edit.setText(date.today().isoformat())
            self.log.append(f"[ok] preset documental aplicado: {selected}")

        def apply_settings(self) -> None:
            self._pandoc_path = Path(self.pandoc_edit.text().strip() or self._pandoc_path)
            self.log.append(f"[ok] ruta pandoc actualizada: {self._pandoc_path}")

        def on_pdf_mode_changed(self, mode: str) -> None:
            engine = self.pdf_engine_edit.text().strip().lower()
            if mode == "native" and (
                "wkhtmltopdf" in engine or engine in {"chrome-headless", "msedge-headless"}
            ):
                self.pdf_engine_edit.clear()
                self.log.append("[info] modo PDF nativo: se limpio motor web configurado.")

        def select_input(self) -> None:
            path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Markdown", "", "Markdown (*.md)")
            if path:
                self.input_edit.setText(path)

        def select_batch_dir(self) -> None:
            path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta para lote", self.batch_dir_edit.text())
            if path:
                self.batch_dir_edit.setText(path)

        def select_profile(self) -> None:
            path, _ = QFileDialog.getOpenFileName(self, "Seleccionar perfil", "", "YAML (*.yaml *.yml)")
            if path:
                self.profile_edit.setText(path)
                self.load_profile_to_form()

        def select_template(self) -> None:
            path, _ = QFileDialog.getOpenFileName(self, "Seleccionar template HTML", "", "HTML (*.html *.htm)")
            if path:
                self.template_html_edit.setText(path)

        def select_template_pdf(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Seleccionar template PDF",
                "",
                "LaTeX (*.tex);;Todos (*.*)",
            )
            if path:
                self.template_pdf_edit.setText(path)

        def select_css(self) -> None:
            path, _ = QFileDialog.getOpenFileName(self, "Seleccionar CSS", "", "CSS (*.css)")
            if path:
                self.css_edit.setText(path)

        def load_profile_to_form(self) -> None:
            profile_path = Path(self.profile_edit.text()).resolve()
            if not profile_path.exists():
                self.log.append(f"[warn] perfil no encontrado: {profile_path}")
                return
            try:
                profile = load_profile(profile_path)
            except Exception as exc:  # pragma: no cover
                QMessageBox.critical(self, "Error de perfil", str(exc))
                return

            self.project_name_edit.setText(profile.project_name)
            self.meta_title_edit.setText(profile.metadata.title or profile.project_name)
            self.meta_subtitle_edit.setText(profile.metadata.subtitle or "")
            self.meta_author_edit.setText(profile.metadata.author or "")
            self.meta_reviewer_edit.setText(profile.metadata.reviewer or "")
            self.meta_version_edit.setText(profile.metadata.version or "")
            self.meta_classification_combo.setCurrentText(profile.metadata.classification)
            self.meta_language_combo.setCurrentText(profile.metadata.language)
            self.meta_date_edit.setText(profile.metadata.date or "")
            self.meta_header_left_edit.setText(profile.metadata.header_left or "")
            self.meta_header_center_edit.setText(profile.metadata.header_center or "")
            self.meta_header_right_edit.setText(profile.metadata.header_right or "")
            self.meta_footer_left_edit.setText(profile.metadata.footer_left or "")
            self.meta_footer_center_edit.setText(profile.metadata.footer_center or "")
            self.meta_footer_right_edit.setText(profile.metadata.footer_right or "")
            self.meta_watermark_edit.setText(profile.metadata.watermark or "")
            self.meta_approver_edit.setText(profile.metadata.approver or "")
            self.meta_approval_date_edit.setText(profile.metadata.approval_date or "")
            self.meta_signatures_check.setChecked(profile.metadata.signatures_enabled)
            output_html = next((x for x in profile.outputs if x.format == "html"), None)
            output_pdf = next((x for x in profile.outputs if x.format == "pdf"), None)
            output_docx = next((x for x in profile.outputs if x.format == "docx"), None)
            output_epub = next((x for x in profile.outputs if x.format == "epub"), None)
            self.output_html_check.setChecked(output_html is not None)
            self.output_pdf_check.setChecked(output_pdf is not None)
            self.output_docx_check.setChecked(output_docx is not None)
            self.output_epub_check.setChecked(output_epub is not None)
            if output_html:
                self.output_html_edit.setText(str(output_html.output_path))
            if output_pdf:
                self.output_pdf_edit.setText(str(output_pdf.output_path))
            if output_docx:
                self.output_docx_edit.setText(str(output_docx.output_path))
            if output_epub:
                self.output_epub_edit.setText(str(output_epub.output_path))
            self.pdf_engine_edit.setText(profile.style_profile.pdf_engine or "")
            self.pdf_layout_mode_combo.setCurrentText(profile.style_profile.pdf_layout_mode)
            self.template_html_edit.setText(str(profile.style_profile.template_html or ""))
            self.template_pdf_edit.setText(str(profile.style_profile.template_pdf or ""))
            self.css_edit.setText(str(profile.style_profile.css or ""))
            self.on_pdf_mode_changed(self.pdf_layout_mode_combo.currentText())
            self.rule_heading_check.setChecked(profile.rules.normalize_headings)
            self.rule_fences_check.setChecked(profile.rules.fix_code_fences)
            self.rule_links_check.setChecked(profile.rules.sanitize_links)
            self._style_options = profile.style_profile.options.model_copy(deep=True)
            self._refresh_style_summary()

        def build_profile_from_form(self) -> ConversionProfile:
            outputs: list[OutputTarget] = []
            if self.output_html_check.isChecked():
                outputs.append(OutputTarget(format="html", output_path=Path(self.output_html_edit.text())))
            if self.output_pdf_check.isChecked():
                outputs.append(OutputTarget(format="pdf", output_path=Path(self.output_pdf_edit.text())))
            if self.output_docx_check.isChecked():
                outputs.append(OutputTarget(format="docx", output_path=Path(self.output_docx_edit.text())))
            if self.output_epub_check.isChecked():
                outputs.append(OutputTarget(format="epub", output_path=Path(self.output_epub_edit.text())))
            if not outputs:
                raise ValueError("Debes habilitar al menos una salida (HTML, PDF, DOCX o EPUB).")
            if not self.project_name_edit.text().strip():
                raise ValueError("El campo Proyecto no puede estar vacio.")
            if not self.input_edit.text().strip():
                raise ValueError("Debes seleccionar un archivo Markdown de entrada.")
            if self.output_html_check.isChecked() and not self.output_html_edit.text().strip():
                raise ValueError("Debes indicar ruta de salida HTML.")
            if self.output_pdf_check.isChecked() and not self.output_pdf_edit.text().strip():
                raise ValueError("Debes indicar ruta de salida PDF.")
            if self.output_docx_check.isChecked() and not self.output_docx_edit.text().strip():
                raise ValueError("Debes indicar ruta de salida DOCX.")
            if self.output_epub_check.isChecked() and not self.output_epub_edit.text().strip():
                raise ValueError("Debes indicar ruta de salida EPUB.")
            if self.output_pdf_check.isChecked() and not self.meta_title_edit.text().strip():
                raise ValueError("Para PDF debes indicar un Titulo documental.")
            normalized_date = self._normalize_iso_date(self.meta_date_edit.text().strip())
            normalized_approval_date = self._normalize_iso_date(self.meta_approval_date_edit.text().strip())
            selected_pdf_mode = self.pdf_layout_mode_combo.currentText().strip() or "web"
            selected_pdf_engine = self.pdf_engine_edit.text().strip() or None
            if selected_pdf_mode == "native" and selected_pdf_engine:
                lower_engine = selected_pdf_engine.lower()
                if "wkhtmltopdf" in lower_engine or lower_engine in {"chrome-headless", "msedge-headless"}:
                    selected_pdf_engine = None
                    self.pdf_engine_edit.clear()
                    self.log.append("[info] modo PDF nativo: motor web descartado automaticamente.")
            if self.meta_signatures_check.isChecked() and not self.meta_approver_edit.text().strip():
                raise ValueError("Si activas Bloque firmas, debes indicar Aprobador.")
            if (
                self.meta_signatures_check.isChecked()
                and self.meta_approver_edit.text().strip()
                and not normalized_approval_date
            ):
                raise ValueError("Si activas Bloque firmas, debes indicar Fecha aprobacion.")

            return ConversionProfile(
                project_name=self.project_name_edit.text().strip() or "Reporte",
                outputs=outputs,
                style_profile=StyleProfile(
                    pdf_engine=selected_pdf_engine,
                    pdf_layout_mode=selected_pdf_mode,
                    template_html=Path(self.template_html_edit.text().strip())
                    if self.template_html_edit.text().strip()
                    else None,
                    template_pdf=Path(self.template_pdf_edit.text().strip())
                    if self.template_pdf_edit.text().strip()
                    else None,
                    css=Path(self.css_edit.text().strip()) if self.css_edit.text().strip() else None,
                    options=self._style_options.model_copy(deep=True),
                ),
                metadata={
                    "title": self.meta_title_edit.text().strip() or self.project_name_edit.text().strip() or None,
                    "subtitle": self.meta_subtitle_edit.text().strip() or None,
                    "author": self.meta_author_edit.text().strip() or None,
                    "reviewer": self.meta_reviewer_edit.text().strip() or None,
                    "version": self.meta_version_edit.text().strip() or None,
                    "classification": self.meta_classification_combo.currentText(),
                    "language": self.meta_language_combo.currentText(),
                    "date": normalized_date,
                    "header_left": self.meta_header_left_edit.text().strip() or None,
                    "header_center": self.meta_header_center_edit.text().strip() or None,
                    "header_right": self.meta_header_right_edit.text().strip() or None,
                    "footer_left": self.meta_footer_left_edit.text().strip() or None,
                    "footer_center": self.meta_footer_center_edit.text().strip() or None,
                    "footer_right": self.meta_footer_right_edit.text().strip() or None,
                    "watermark": self.meta_watermark_edit.text().strip() or None,
                    "approver": self.meta_approver_edit.text().strip() or None,
                    "approval_date": normalized_approval_date,
                    "signatures_enabled": self.meta_signatures_check.isChecked(),
                },
                rules=RuleSet(
                    normalize_headings=self.rule_heading_check.isChecked(),
                    fix_code_fences=self.rule_fences_check.isChecked(),
                    sanitize_links=self.rule_links_check.isChecked(),
                ),
            )

        def _validate_convert_inputs(self, input_path: Path, profile_path: Path, profile: ConversionProfile) -> None:
            if not input_path.exists():
                raise FileNotFoundError(f"No existe el archivo de entrada: {input_path}")
            if input_path.suffix.lower() != ".md":
                raise ValueError("El input debe ser un archivo Markdown (*.md).")
            if not profile_path.parent.exists():
                raise FileNotFoundError(f"La carpeta del perfil no existe: {profile_path.parent}")
            if profile.style_profile.template_html and not profile.style_profile.template_html.exists():
                raise FileNotFoundError(f"No existe template HTML: {profile.style_profile.template_html}")
            if profile.style_profile.template_pdf and not profile.style_profile.template_pdf.exists():
                raise FileNotFoundError(f"No existe template PDF: {profile.style_profile.template_pdf}")
            if profile.style_profile.css and not profile.style_profile.css.exists():
                raise FileNotFoundError(f"No existe archivo CSS: {profile.style_profile.css}")

        @staticmethod
        def _normalize_iso_date(value: str) -> str | None:
            if not value:
                return None
            try:
                parsed = date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Fecha invalida. Usa formato YYYY-MM-DD.") from exc
            return parsed.isoformat()

        def save_profile_from_form(self) -> None:
            profile_path = Path(self.profile_edit.text()).resolve()
            try:
                profile = self.build_profile_from_form()
                save_profile(profile, profile_path)
                self.log.append(f"[ok] perfil guardado en {profile_path}")
            except Exception as exc:  # pragma: no cover
                QMessageBox.critical(self, "Error guardando perfil", str(exc))

        def refresh_history(self) -> None:
            entries = read_history(self.history_path, limit=250)
            self.history_table.setRowCount(len(entries))
            for idx, entry in enumerate(entries):
                self.history_table.setItem(idx, 0, QTableWidgetItem(str(entry.get("timestamp", ""))))
                self.history_table.setItem(idx, 1, QTableWidgetItem(str(entry.get("format", ""))))
                self.history_table.setItem(idx, 2, QTableWidgetItem(str(entry.get("return_code", ""))))
                self.history_table.setItem(idx, 3, QTableWidgetItem(str(entry.get("output_path", ""))))
            self.refresh_dashboard_metrics(entries)

        def refresh_dashboard_metrics(self, entries: list[dict] | None = None) -> None:
            if entries is None:
                entries = read_history(self.history_path, limit=250)
            total = len(entries)
            ok = sum(1 for e in entries if int(e.get("return_code", 1)) == 0)
            err = total - ok
            self.metric_total.setText(str(total))
            self.metric_ok.setText(str(ok))
            self.metric_err.setText(str(err))

        def update_html_preview(self, maybe_html_path: Path) -> None:
            if maybe_html_path.exists():
                self.preview.setSource(QUrl.fromLocalFile(str(maybe_html_path.resolve())))
            else:
                self.preview.setHtml("<h3>Sin vista previa</h3><p>No se encontro archivo HTML generado.</p>")

        def open_last_html(self) -> None:
            if self._last_html_output and self._last_html_output.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_html_output.resolve())))
                return
            entries = read_history(self.history_path, limit=250)
            html_entry = next((entry for entry in entries if entry.get("format") == "html"), None)
            if not html_entry:
                QMessageBox.information(self, "DocsConverter", "No hay conversiones HTML en historial.")
                return
            output_path = Path(str(html_entry.get("output_path", ""))).resolve()
            if not output_path.exists():
                QMessageBox.warning(self, "DocsConverter", f"No existe el archivo: {output_path}")
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path)))

        def open_last_pdf(self) -> None:
            if self._last_pdf_output and self._last_pdf_output.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_pdf_output.resolve())))
                return
            if self._last_run_pdf_requested and self._last_run_pdf_failed:
                QMessageBox.warning(
                    self,
                    "DocsConverter",
                    "El PDF de la ultima ejecucion fallo. No se abrira un PDF antiguo del historial.",
                )
                return
            entries = read_history(self.history_path, limit=250)
            pdf_entry = next((entry for entry in entries if entry.get("format") == "pdf"), None)
            if not pdf_entry:
                QMessageBox.information(self, "DocsConverter", "No hay conversiones PDF en historial.")
                return
            output_path = Path(str(pdf_entry.get("output_path", ""))).resolve()
            if not output_path.exists():
                QMessageBox.warning(self, "DocsConverter", f"No existe el archivo: {output_path}")
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path)))

        def open_last_docx(self) -> None:
            if self._last_docx_output and self._last_docx_output.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_docx_output.resolve())))
                return
            entries = read_history(self.history_path, limit=250)
            docx_entry = next((entry for entry in entries if entry.get("format") == "docx"), None)
            if not docx_entry:
                QMessageBox.information(self, "DocsConverter", "No hay conversiones DOCX en historial.")
                return
            output_path = Path(str(docx_entry.get("output_path", ""))).resolve()
            if not output_path.exists():
                QMessageBox.warning(self, "DocsConverter", f"No existe el archivo: {output_path}")
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path)))

        def open_last_epub(self) -> None:
            if self._last_epub_output and self._last_epub_output.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_epub_output.resolve())))
                return
            entries = read_history(self.history_path, limit=250)
            epub_entry = next((entry for entry in entries if entry.get("format") == "epub"), None)
            if not epub_entry:
                QMessageBox.information(self, "DocsConverter", "No hay conversiones EPUB en historial.")
                return
            output_path = Path(str(epub_entry.get("output_path", ""))).resolve()
            if not output_path.exists():
                QMessageBox.warning(self, "DocsConverter", f"No existe el archivo: {output_path}")
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path)))

        def _open_progress(self, message: str) -> None:
            self._progress_dialog = QProgressDialog(message, "", 0, 100, self)
            self._progress_dialog.setWindowTitle("Convirtiendo")
            self._progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            self._progress_dialog.setCancelButton(None)
            self._progress_dialog.setMinimumDuration(0)
            self._progress_dialog.setValue(0)
            self._progress_dialog.show()
            self.btn_convert.setEnabled(False)
            if hasattr(self, "btn_convert_batch"):
                self.btn_convert_batch.setEnabled(False)

        def _update_progress(self, value: int, message: str) -> None:
            if self._progress_dialog:
                self._progress_dialog.setLabelText(message)
                self._progress_dialog.setValue(max(0, min(100, value)))

        def _close_progress(self) -> None:
            if self._progress_dialog:
                self._progress_dialog.close()
                self._progress_dialog.deleteLater()
                self._progress_dialog = None
            self.btn_convert.setEnabled(True)
            if hasattr(self, "btn_convert_batch"):
                self.btn_convert_batch.setEnabled(True)

        def _cleanup_conversion_thread(self) -> None:
            if self._conversion_thread:
                self._conversion_thread.quit()
                self._conversion_thread.wait()
                self._conversion_thread.deleteLater()
            self._conversion_thread = None
            self._conversion_worker = None

        def _on_conversion_finished(self, payload: object) -> None:
            data = payload if isinstance(payload, dict) else {}
            results = data.get("results", [])
            detected_engine = data.get("detected_engine")
            fallback_warning = data.get("fallback_warning")
            had_configured_pdf_engine = bool(data.get("had_configured_pdf_engine", False))
            batch_mode = bool(data.get("batch_mode", False))
            batch_count = int(data.get("batch_count", 0))
            pdf_mode = str(data.get("pdf_mode", "") or "")
            pdf_engine = str(data.get("pdf_engine", "") or "")

            self.log.clear()
            if fallback_warning:
                self.log.append(str(fallback_warning))
            if detected_engine and not had_configured_pdf_engine:
                self.log.append(f"[preflight] motor PDF auto-detectado: {detected_engine}")
            if pdf_mode:
                self.log.append(f"[run] modo PDF: {pdf_mode}")
            if pdf_engine:
                self.log.append(f"[run] motor PDF: {pdf_engine}")
            if batch_mode:
                self._append_batch_summary(results, batch_count)
                self._auto_export_batch_summary()
            else:
                self._last_batch_summary_text = None
                self._last_batch_summary_json = None
                self._last_batch_summary_rows = []
                self.batch_summary_table.setRowCount(0)

            self._last_html_output = None
            self._last_pdf_output = None
            self._last_docx_output = None
            self._last_epub_output = None
            self._last_run_pdf_requested = False
            self._last_run_pdf_failed = False
            has_errors = False
            for result in results:
                self.log.append(
                    f"{result.output.format}: rc={result.return_code} "
                    f"elapsed={result.elapsed_seconds:.2f}s timeout={result.timed_out} "
                    f"-> {result.output.output_path}"
                )
                if result.stderr.strip():
                    self.log.append(result.stderr.strip())
                if int(result.return_code) != 0:
                    has_errors = True
                if result.output.format == "html" and int(result.return_code) == 0:
                    self._last_html_output = result.output.output_path
                if result.output.format == "pdf":
                    self._last_run_pdf_requested = True
                    if int(result.return_code) != 0:
                        self._last_run_pdf_failed = True
                if result.output.format == "pdf" and int(result.return_code) == 0:
                    self._last_pdf_output = result.output.output_path
                if result.output.format == "docx" and int(result.return_code) == 0:
                    self._last_docx_output = result.output.output_path
                if result.output.format == "epub" and int(result.return_code) == 0:
                    self._last_epub_output = result.output.output_path
            if self._last_html_output:
                self.update_html_preview(self._last_html_output)
            self.refresh_history()
            self._close_progress()
            self._cleanup_conversion_thread()
            if batch_mode:
                if has_errors:
                    QMessageBox.warning(
                        self,
                        "DocsConverter",
                        f"Conversion por lote finalizada con errores. Archivos procesados: {batch_count}",
                    )
                else:
                    QMessageBox.information(
                        self,
                        "DocsConverter",
                        f"Conversion por lote finalizada. Archivos procesados: {batch_count}",
                    )
            else:
                if has_errors:
                    QMessageBox.warning(self, "DocsConverter", "Conversion finalizada con errores. Revisa Logs.")
                else:
                    QMessageBox.information(self, "DocsConverter", "Conversion finalizada")

        def _append_batch_summary(self, results: list, batch_count: int) -> None:
            if not results:
                self.log.append("[batch] sin resultados.")
                return
            total_outputs = len(results)
            total_errors = sum(1 for r in results if int(getattr(r, "return_code", 1)) != 0)
            lines: list[str] = []
            lines.append(f"[batch] archivos procesados: {batch_count}")
            lines.append(f"[batch] salidas generadas: {total_outputs}")
            lines.append(f"[batch] salidas con error: {total_errors}")
            lines.append("[batch] detalle por archivo:")

            grouped: dict[str, list] = {}
            for result in results:
                output_path = Path(str(result.output.output_path))
                key = output_path.stem
                grouped.setdefault(key, []).append(result)

            detail_rows: list[dict[str, str | int]] = []

            for file_key in sorted(grouped.keys()):
                lines.append(f"  - {file_key}")
                for result in grouped[file_key]:
                    status = "OK" if result.return_code == 0 else f"ERR({result.return_code})"
                    lines.append(f"      {result.output.format.upper():<5} {status} -> {result.output.output_path}")
                    detail_rows.append(
                        {
                            "file": file_key,
                            "format": result.output.format,
                            "status": status,
                            "return_code": int(result.return_code),
                            "output_path": str(result.output.output_path),
                            "stderr": str(result.stderr).strip(),
                        }
                    )

            self._last_batch_summary_text = "\n".join(lines)
            self._last_batch_summary_json = {
                "files_processed": batch_count,
                "outputs_generated": total_outputs,
                "outputs_with_error": total_errors,
                "details": detail_rows,
            }
            self._last_batch_summary_rows = detail_rows
            self._populate_batch_summary_table()
            self.log.append(self._last_batch_summary_text)

        def _populate_batch_summary_table(self) -> None:
            rows = self._last_batch_summary_rows
            self.batch_summary_table.setRowCount(len(rows))
            for idx, row in enumerate(rows):
                self.batch_summary_table.setItem(idx, 0, QTableWidgetItem(str(row.get("file", ""))))
                self.batch_summary_table.setItem(idx, 1, QTableWidgetItem(str(row.get("format", "")).upper()))
                self.batch_summary_table.setItem(idx, 2, QTableWidgetItem(str(row.get("status", ""))))
                self.batch_summary_table.setItem(idx, 3, QTableWidgetItem(str(row.get("return_code", ""))))
                self.batch_summary_table.setItem(idx, 4, QTableWidgetItem(str(row.get("output_path", ""))))

        def export_batch_summary(self) -> None:
            if not self._last_batch_summary_text or not self._last_batch_summary_json:
                QMessageBox.information(self, "DocsConverter", "No hay resumen de lote para exportar.")
                return
            path, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Exportar resumen de lote",
                "build/output/batch-summary.txt",
                "Texto (*.txt);;JSON (*.json)",
            )
            if not path:
                return
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if "JSON" in selected_filter or target.suffix.lower() == ".json":
                target.write_text(json.dumps(self._last_batch_summary_json, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                target.write_text(self._last_batch_summary_text, encoding="utf-8")
            self.log.append(f"[batch] resumen exportado: {target}")

        def _auto_export_batch_summary(self) -> None:
            if not self._last_batch_summary_text or not self._last_batch_summary_json:
                return
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            out_dir = Path("logs/batch")
            out_dir.mkdir(parents=True, exist_ok=True)
            txt_path = out_dir / f"batch-summary-{timestamp}.txt"
            json_path = out_dir / f"batch-summary-{timestamp}.json"
            txt_path.write_text(self._last_batch_summary_text, encoding="utf-8")
            json_path.write_text(
                json.dumps(self._last_batch_summary_json, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.log.append(f"[batch] autoexport txt: {txt_path}")
            self.log.append(f"[batch] autoexport json: {json_path}")

        def _on_conversion_failed(self, error_message: str) -> None:
            self._close_progress()
            self._cleanup_conversion_thread()
            QMessageBox.critical(self, "Error", error_message)

        def convert(self) -> None:
            input_path = Path(self.input_edit.text()).resolve()
            profile_path = Path(self.profile_edit.text()).resolve()
            try:
                profile = self.build_profile_from_form()
                self._validate_convert_inputs(input_path, profile_path, profile)
                had_configured_pdf_engine = bool(profile.style_profile.pdf_engine)
                job = ConversionJob(
                    input_path=input_path,
                    profile_path=profile_path,
                    outputs=profile.outputs,
                    style_profile=profile.style_profile,
                    metadata=profile.metadata,
                    rules=profile.rules,
                )
                if not job.metadata.title:
                    job.metadata.title = profile.project_name
                self._open_progress("Preparando conversion...")
                self._conversion_thread = QThread(self)
                self._conversion_worker = ConversionWorker(
                    job=job,
                    pandoc_path_value=self._pandoc_path,
                    history_path_value=self.history_path,
                    had_configured_pdf_engine=had_configured_pdf_engine,
                    sanitization_config=getattr(self, '_temp_sanitization_config', None),
                )
                self._conversion_worker.moveToThread(self._conversion_thread)
                self._conversion_thread.started.connect(self._conversion_worker.run)
                self._conversion_worker.progress.connect(self._update_progress)
                self._conversion_worker.finished.connect(self._on_conversion_finished)
                self._conversion_worker.failed.connect(self._on_conversion_failed)
                self._conversion_thread.start()
            except Exception as exc:  # pragma: no cover
                QMessageBox.critical(self, "Error", str(exc))

        def convert_batch(self) -> None:
            profile_path = Path(self.profile_edit.text()).resolve()
            input_dir = Path(self.batch_dir_edit.text()).resolve()
            pattern = self.batch_pattern_edit.text().strip() or "*.md"
            recursive = self.batch_recursive_check.isChecked()
            try:
                profile = self.build_profile_from_form()
                if not input_dir.exists() or not input_dir.is_dir():
                    raise ValueError(f"Carpeta de lote no valida: {input_dir}")
                if not pattern:
                    raise ValueError("Debes indicar un patron de archivos, por ejemplo *.md")
                if profile.style_profile.template_html and not profile.style_profile.template_html.exists():
                    raise FileNotFoundError(f"No existe template HTML: {profile.style_profile.template_html}")
                if profile.style_profile.css and not profile.style_profile.css.exists():
                    raise FileNotFoundError(f"No existe archivo CSS: {profile.style_profile.css}")

                had_configured_pdf_engine = bool(profile.style_profile.pdf_engine)
                self._open_progress("Preparando conversion por lote...")
                self._conversion_thread = QThread(self)
                self._conversion_worker = BatchConversionWorker(
                    profile=profile,
                    input_dir=input_dir,
                    pattern=pattern,
                    recursive=recursive,
                    pandoc_path_value=self._pandoc_path,
                    history_path_value=self.history_path,
                    had_configured_pdf_engine=had_configured_pdf_engine,
                )
                self._conversion_worker.moveToThread(self._conversion_thread)
                self._conversion_thread.started.connect(self._conversion_worker.run)
                self._conversion_worker.progress.connect(self._update_progress)
                self._conversion_worker.finished.connect(self._on_conversion_finished)
                self._conversion_worker.failed.connect(self._on_conversion_failed)
                self._conversion_thread.start()
                self.log.append(
                    f"[batch] iniciando carpeta={input_dir} patron={pattern} recursivo={recursive} perfil={profile_path}"
                )
            except Exception as exc:  # pragma: no cover
                QMessageBox.critical(self, "Error", str(exc))

    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
