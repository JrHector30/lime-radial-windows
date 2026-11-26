"""
Detector global inteligente de Shift + Drag para Windows.
Garantiza que el menú radial NUNCA se active en juegos, navegadores o aplicaciones ajenas.
Sólo se activa cuando el usuario arrastra archivos reales desde el Explorador de Windows o el Escritorio.
"""
from __future__ import annotations

import ctypes
import os
import sys
from typing import Callable, List, Optional

from PySide6.QtCore import QObject, QPoint, QTimer, Signal
from PySide6.QtGui import QCursor

VK_LBUTTON = 0x01
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_ALT = 0x12
VK_ESCAPE = 0x1B

DRAG_THRESHOLD = 14       # Píxeles mínimos de desplazamiento arrastrando
IDLE_TIMEOUT_TICKS = 25   # ~350 ms si no llega ningún evento OLE de archivo real

# Clases nativas de Windows para el Explorador de Archivos y el Escritorio
EXPLORER_WINDOW_CLASSES = {
    "CabinetWClass",       # Carpetas del Explorador de Windows (Windows 10 / 11)
    "ExploreWClass",       # Explorador clásico
    "Progman",             # Escritorio de Windows
    "WorkerW",             # Escritorio con wallpaper dinámico
    "SysDragImage",        # Imagen flotante de arrastre del sistema
    "DirectUIHWND",        # Área de archivos interna
    "SysListView32",       # Lista de iconos clásica
}


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class DragShiftWatcher(QObject):
    show_menu = Signal(QPoint, list)
    hide_menu = Signal()

    def __init__(
        self,
        is_menu_visible: Callable[[], bool],
        has_menu_drag: Callable[[], bool],
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.is_menu_visible = is_menu_visible
        self.has_menu_drag = has_menu_drag
        self.enabled = True
        self.trigger_vk = VK_SHIFT
        self.key_name = "Shift"

        self._down_at: Optional[QPoint] = None
        self._down_in_explorer: bool = False
        self._fired = False
        self._idle_ticks = 0
        self._shown_at = QPoint()

        self._user32 = ctypes.windll.user32 if sys.platform == "win32" else None
        self._timer = QTimer(self)
        self._timer.setInterval(15)
        self._timer.timeout.connect(self._tick)

    def set_trigger_key(self, name: str):
        mapping = {"Shift": VK_SHIFT, "Ctrl": VK_CONTROL, "Alt": VK_ALT}
        self.key_name = name
        self.trigger_vk = mapping.get(name, VK_SHIFT)

    def start(self):
        if self._user32:
            self._timer.start()

    def stop(self):
        self._timer.stop()

    def _is_down(self, vk: int) -> bool:
        if not self._user32:
            return False
        return bool(self._user32.GetAsyncKeyState(vk) & 0x8000)

    def _is_explorer_or_file_context(self, pos: QPoint) -> bool:
        """
        Verifica si el clic o arrastre proviene de una ventana del Explorador/Escritorio
        o si existe la ventana de arrastre del sistema 'SysDragImage'.
        Evita al 100% que se active mientras juegas o usas otras apps.
        """
        if not self._user32:
            return False

        # 1. Si Windows ya creó la ventana de arrastre de archivos SysDragImage
        if self._user32.FindWindowW("SysDragImage", None) != 0:
            return True

        # 2. Verificar la ventana debajo del cursor donde empezó el clic
        pt = POINT(pos.x(), pos.y())
        hwnd = self._user32.WindowFromPoint(pt)
        if not hwnd:
            return False

        # Obtener clase de la ventana directa y de la ventana raíz
        buf = ctypes.create_unicode_buffer(256)
        self._user32.GetClassNameW(hwnd, buf, 256)
        direct_class = buf.value

        root_hwnd = self._user32.GetAncestor(hwnd, 2)  # GA_ROOT = 2
        root_class = ""
        if root_hwnd:
            self._user32.GetClassNameW(root_hwnd, buf, 256)
            root_class = buf.value

        return (
            direct_class in EXPLORER_WINDOW_CLASSES
            or root_class in EXPLORER_WINDOW_CLASSES
        )

    def _get_selected_files_at_cursor(self, pos: QPoint) -> List[str]:
        """
        Obtiene los archivos reales actualmente seleccionados en el Explorador o Escritorio.
        Retorna lista vacía si el usuario hizo clic en una zona vacía de la carpeta o el escritorio.
        """
        if sys.platform != "win32" or not self._user32:
            return []
        try:
            import win32com.client
            pt = POINT(pos.x(), pos.y())
            hwnd = self._user32.WindowFromPoint(pt)
            if not hwnd:
                return []
            root_hwnd = self._user32.GetAncestor(hwnd, 2) or hwnd

            buf = ctypes.create_unicode_buffer(256)
            self._user32.GetClassNameW(hwnd, buf, 256)
            d_cls = buf.value
            self._user32.GetClassNameW(root_hwnd, buf, 256)
            r_cls = buf.value

            is_desktop = d_cls in ("Progman", "WorkerW", "SysListView32") or r_cls in ("Progman", "WorkerW")
            is_explorer = d_cls in ("CabinetWClass", "ExploreWClass", "DirectUIHWND") or r_cls in ("CabinetWClass", "ExploreWClass")

            if not (is_desktop or is_explorer):
                return []

            shell = win32com.client.Dispatch("Shell.Application")
            sw = shell.Windows()

            # Caso 1: Escritorio de Windows
            if is_desktop:
                try:
                    desktop = sw.FindWindowSW(0, 0, 8, 0, 1)  # SWC_DESKTOP=8, SWFO_NEEDDISPATCH=1
                    if desktop:
                        items = desktop.Document.SelectedItems()
                        return [
                            item.Path for item in items
                            if hasattr(item, "Path") and os.path.isfile(item.Path)
                        ]
                except Exception:
                    pass
                return []

            # Caso 2: Ventana de Explorador de archivos
            if is_explorer:
                rect = (ctypes.c_long * 4)()
                for w in sw:
                    try:
                        if w.HWND == root_hwnd or w.HWND == hwnd:
                            items = w.Document.SelectedItems()
                            return [
                                item.Path for item in items
                                if hasattr(item, "Path") and os.path.isfile(item.Path)
                            ]
                        self._user32.GetWindowRect(w.HWND, ctypes.byref(rect))
                        if rect[0] <= pos.x() <= rect[2] and rect[1] <= pos.y() <= rect[3]:
                            items = w.Document.SelectedItems()
                            return [
                                item.Path for item in items
                                if hasattr(item, "Path") and os.path.isfile(item.Path)
                            ]
                    except Exception:
                        pass
                return []
        except Exception:
            pass
        return []

    def _tick(self):
        if not self.enabled:
            return

        lbtn = self._is_down(VK_LBUTTON)
        trigger = self._is_down(self.trigger_vk)
        esc = self._is_down(VK_ESCAPE)
        pos = QCursor.pos()

        if self.is_menu_visible():
            if not lbtn or esc:
                # El usuario soltó el clic o canceló
                QTimer.singleShot(80, self.hide_menu.emit)
            elif not self.has_menu_drag():
                # Si el menú apareció pero no llegó ningún drag OLE de archivos reales,
                # ocultar de inmediato para no estorbar
                dist = (pos - self._shown_at).manhattanLength()
                if dist > 6:
                    self._idle_ticks += 1
                    if self._idle_ticks > IDLE_TIMEOUT_TICKS:
                        self.hide_menu.emit()
        else:
            if lbtn:
                if self._down_at is None:
                    self._down_at = pos
                    self._fired = False
                    # Verificar al hacer clic si estamos en el Explorador o Escritorio
                    self._down_in_explorer = self._is_explorer_or_file_context(pos)

                moved = (pos - self._down_at).manhattanLength() >= DRAG_THRESHOLD

                # SÓLO se dispara si empezó en el explorador/escritorio
                if moved and trigger and self._down_in_explorer and not self._fired:
                    self._fired = True
                    # Comprobar si realmente hay ARCHIVOS seleccionados bajo el cursor (NUNCA carpetas)
                    files = self._get_selected_files_at_cursor(self._down_at or pos)
                    real_files = [f for f in files if os.path.isfile(f)]

                    # Si NO hay archivos seleccionados o solo se seleccionaron carpetas, NO mostrar el menú
                    if real_files:
                        self._idle_ticks = 0
                        self._shown_at = pos
                        self.show_menu.emit(pos, real_files)
            else:
                self._down_at = None
                self._down_in_explorer = False
                self._fired = False
