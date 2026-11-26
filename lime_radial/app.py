"""
Coordinador principal de la aplicación Lime Radial Windows.
Completamente silencioso y conectado con todas las sub-herramientas:
Crop, Edit, Add BG, Redact, Annotate, Compress, Create PDF, Collage, Metadata y ventana About.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, QPoint, QRunnable, QThreadPool, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication

from .about import AboutDialog
from .convert import convert_files
from .radial import RadialMenu
from .tools_ui import (
    AddBgDialog,
    AnnotateImageDialog,
    CropImageDialog,
    EditImageDialog,
    RedactImageDialog,
    execute_collage,
    execute_compress,
    execute_create_pdf,
    execute_metadata_strip,
)
from .tray import LimeTray
from .trigger import DragShiftWatcher
from .updater import check_for_updates


class ActionTask(QRunnable):
    def __init__(self, action_fn, *args):
        super().__init__()
        self.action_fn = action_fn
        self.args = args

    def run(self):
        try:
            self.action_fn(*self.args)
        except Exception as e:
            print(f"[LimeRadial Error]: {e}", file=sys.stderr)


class LimeApp(QObject):
    def __init__(self, qapp: QApplication):
        super().__init__()
        self.qapp = qapp
        self.qapp.setQuitOnLastWindowClosed(False)
        self.thread_pool = QThreadPool.globalInstance()

        # 1. Menú radial flotante
        self.radial_menu = RadialMenu(size=380)
        self.radial_menu.file_dropped.connect(self._on_files_dropped)
        self.radial_menu.tool_triggered.connect(self._on_tool_triggered)

        # 2. Detector inteligente de Shift + Drag (Sólo en Explorador/Escritorio)
        self.watcher = DragShiftWatcher(
            is_menu_visible=self.radial_menu.isVisible,
            has_menu_drag=lambda: self.radial_menu.has_drag,
        )
        self.watcher.show_menu.connect(self._on_trigger_show)
        self.watcher.hide_menu.connect(self._on_trigger_hide)

        # 3. Icono en bandeja de sistema
        self.tray = LimeTray(
            on_toggle_enabled=self._on_toggle_watcher,
            on_change_key=self.watcher.set_trigger_key,
            on_test_menu=self._on_test_menu,
            on_check_updates=self._on_check_updates,
            on_about=self._on_about,
            on_quit=self._on_quit,
        )
        self.tray.show()

        # Iniciar monitoreo global
        self.watcher.start()

    def _on_trigger_show(self, pos: QPoint, paths: Optional[List[str]] = None):
        self.radial_menu.popup_at(pos, paths=paths)

    def _on_trigger_hide(self):
        self.radial_menu.close_menu()

    def _on_test_menu(self):
        pos = QCursor.pos()
        self.radial_menu.popup_at(pos)

    def _on_check_updates(self):
        """Abre la comprobación de actualizaciones automáticas."""
        check_for_updates()

    def _on_about(self):
        """Abre la ventana informativa Acerca de / About."""
        dlg = AboutDialog()
        dlg.exec()

    def _on_toggle_watcher(self, enabled: bool):
        self.watcher.enabled = enabled

    def _on_files_dropped(self, paths: List[str], target_format: str):
        """Conversión de formatos completamente silenciosa."""
        task = ActionTask(convert_files, paths, target_format)
        self.thread_pool.start(task)

    def _on_tool_triggered(self, tool_name: str, paths: List[str]):
        """Manejo de herramientas avanzadas interactivas y automáticas en Español e Inglés."""
        name = tool_name.upper().replace("TO ", "").strip()

        if name in ("CROP", "RECORTAR") and paths:
            dialog = CropImageDialog(paths[0])
            dialog.exec()

        elif name in ("EDIT", "EDITAR") and paths:
            dialog = EditImageDialog(paths[0])
            dialog.exec()

        elif name in ("ADD BG", "ADDBG", "BACKGROUND", "AÑADIR FONDO", "FONDO") and paths:
            dialog = AddBgDialog(paths[0])
            dialog.exec()

        elif name in ("REDACT", "CENSURAR") and paths:
            dialog = RedactImageDialog(paths[0])
            dialog.exec()

        elif name in ("ANNOTATE", "ANOTAR") and paths:
            dialog = AnnotateImageDialog(paths[0])
            dialog.exec()

        elif name in ("COMPRESS", "COMPRIMIR"):
            task = ActionTask(convert_files, paths, "COMPRIMIR")
            self.thread_pool.start(task)

        elif name in ("CREATE PDF", "CREAR PDF", "PDF"):
            task = ActionTask(convert_files, paths, "CREAR PDF")
            self.thread_pool.start(task)

        elif name in ("DIVIDIR PDF", "SPLIT PDF", "DIVIDIR", "SPLIT"):
            task = ActionTask(convert_files, paths, "DIVIDIR PDF")
            self.thread_pool.start(task)

        elif name in ("APLANAR PDF", "FLATTEN PDF", "APLANAR", "FLATTEN"):
            task = ActionTask(convert_files, paths, "APLANAR PDF")
            self.thread_pool.start(task)

        elif name == "COLLAGE":
            task = ActionTask(execute_collage, paths)
            self.thread_pool.start(task)

        elif name in ("METADATA", "METADATOS"):
            task = ActionTask(execute_metadata_strip, paths)
            self.thread_pool.start(task)
        else:
            task = ActionTask(convert_files, paths, tool_name)
            self.thread_pool.start(task)

    def _on_quit(self):
        self.watcher.stop()
        self.radial_menu.close_menu()
        self.tray.hide()
        self.qapp.quit()
