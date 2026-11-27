"""
Módulo de actualización automática para Lime Radial Windows.
Diseñado con Glassmorphism auténtico basado en CheckForUpdatesModal.tsx:
- Icono cítrico LimeFruitIcon en mosaico brillante
- Verificación asíncrona en GitHub Releases
- Descarga en segundo plano con barra de progreso
- Instalación silenciosa y reinicio automático de Lime Radial
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import QObject, QPointF, QRectF, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .icons import FONT_FAMILY, draw_lime_fruit_icon
from .themes import ThemeManager

CURRENT_VERSION = "1.1.8"
GITHUB_REPO = "JrHector30/lime-radial-windows"
RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def parse_version_tuple(v_str: str) -> Tuple[int, ...]:
    clean = v_str.strip().lower().lstrip("v")
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts)


class CheckUpdateThread(QThread):
    finished_check = Signal(bool, str, str, str, int)  # has_update, tag, url, notes, size
    error_occurred = Signal(str)

    def run(self):
        try:
            req = urllib.request.Request(
                RELEASES_API_URL,
                headers={"User-Agent": "LimeRadial-AutoUpdater", "Accept": "application/vnd.github.v3+json"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            release_notes = data.get("body", "") or "Mejoras de rendimiento y correcciones de estabilidad."
            
            latest_tuple = parse_version_tuple(tag_name)
            current_tuple = parse_version_tuple(CURRENT_VERSION)
            has_update = latest_tuple > current_tuple

            download_url = ""
            asset_size = 0
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith("-Setup.exe") or name.endswith(".exe"):
                    download_url = asset.get("browser_download_url", "")
                    asset_size = asset.get("size", 0)
                    break

            self.finished_check.emit(has_update, tag_name, download_url, release_notes, asset_size)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DownloadUpdateThread(QThread):
    progress = Signal(int, int, int)  # percent, downloaded_bytes, total_bytes
    finished = Signal(str)           # local installer path
    error = Signal(str)

    def __init__(self, url: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            dest_dir = Path(tempfile.gettempdir())
            dest_file = dest_dir / "LimeRadial-Setup-Update.exe"

            req = urllib.request.Request(self.url, headers={"User-Agent": "LimeRadial-AutoUpdater"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                total_bytes = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024

                with open(dest_file, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        percent = int((downloaded / total_bytes) * 100) if total_bytes > 0 else 0
                        self.progress.emit(percent, downloaded, total_bytes)

            self.finished.emit(str(dest_file))
        except Exception as e:
            self.error.emit(str(e))


class LimeTileWidget(QWidget):
    """Mosaico central redondeado con resplandor dorado y el icono LimeFruitIcon."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self._is_light = False

    def set_mode(self, is_light: bool):
        self._is_light = is_light
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Resplandor suave de fondo
        glow = QRadialGradient(32, 32, 32)
        glow_alpha = 45 if self._is_light else 35
        glow.setColorAt(0.0, QColor(250, 204, 21, glow_alpha))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), glow)

        # Mosaico de vidrio
        rect = QRectF(4, 4, 56, 56)
        if self._is_light:
            painter.setBrush(QColor(0, 0, 0, 8))
            painter.setPen(QPen(QColor(0, 0, 0, 22), 1.0))
        else:
            painter.setBrush(QColor(255, 255, 255, 14))
            painter.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
        painter.drawRoundedRect(rect, 16, 16)

        # Icono cítrico
        draw_lime_fruit_icon(painter, QRectF(12, 12, 40, 40))


class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar Actualizaciones")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(360, 360)

        self._download_url = ""
        self._new_version = ""
        self._checking = False
        self._has_update = False
        self._has_error = False
        self._drag_pos = None

        self.theme_mgr = ThemeManager.get_instance()
        self.theme_mgr.add_listener(self._apply_theme)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        self.card = QWidget(self)
        self.card.setObjectName("updateCard")
        root.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 16, 20, 20)
        card_layout.setSpacing(10)

        # 1. Barra superior: Título a la izquierda, botón circular de cierre a la derecha
        top_bar = QHBoxLayout()
        self.top_title = QLabel("Buscar Actualizaciones")
        self.top_title.setFont(QFont(FONT_FAMILY, 10))

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(26, 26)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.accept)

        top_bar.addWidget(self.top_title)
        top_bar.addStretch()
        top_bar.addWidget(self.close_btn)
        card_layout.addLayout(top_bar)

        card_layout.addSpacing(6)

        # 2. Mosaico central cítrico
        tile_container = QHBoxLayout()
        tile_container.addStretch()
        self.tile_widget = LimeTileWidget()
        tile_container.addWidget(self.tile_widget)
        tile_container.addStretch()
        card_layout.addLayout(tile_container)

        card_layout.addSpacing(4)

        # 3. Título principal
        self.main_title = QLabel("Comprobando actualizaciones…")
        self.main_title.setAlignment(Qt.AlignCenter)
        self.main_title.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
        card_layout.addWidget(self.main_title)

        # 4. Badge de estado (Check con versión)
        self.badge_lbl = QLabel(f"✓ Versión actual instalada: v{CURRENT_VERSION}")
        self.badge_lbl.setAlignment(Qt.AlignCenter)
        self.badge_lbl.setFont(QFont(FONT_FAMILY, 9, QFont.DemiBold))
        self.badge_lbl.setWordWrap(True)
        card_layout.addWidget(self.badge_lbl)

        # 5. Subtítulo / Descripción
        self.desc_lbl = QLabel("Consultando el servidor oficial de GitHub Releases...")
        self.desc_lbl.setAlignment(Qt.AlignCenter)
        self.desc_lbl.setFont(QFont(FONT_FAMILY, 9))
        self.desc_lbl.setWordWrap(True)
        card_layout.addWidget(self.desc_lbl)

        # 6. Barra de progreso (para descarga de actualización)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setVisible(False)
        card_layout.addWidget(self.progress_bar)

        card_layout.addSpacing(10)

        # 7. Botones inferiores
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(10)

        self.sec_btn = QPushButton("🔄 Comprobar")
        self.sec_btn.setFixedHeight(36)
        self.sec_btn.setCursor(Qt.PointingHandCursor)
        self.sec_btn.clicked.connect(self._recheck)

        self.prim_btn = QPushButton("Entendido")
        self.prim_btn.setFixedHeight(36)
        self.prim_btn.setCursor(Qt.PointingHandCursor)
        self.prim_btn.clicked.connect(self.accept)

        self.btn_layout.addWidget(self.sec_btn)
        self.btn_layout.addWidget(self.prim_btn)
        card_layout.addLayout(self.btn_layout)

        self._apply_theme()
        # Disparar verificación inicial
        self._start_check()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _apply_theme(self, theme=None):
        palette = self.theme_mgr.get_accent_palette()
        is_light = (self.theme_mgr.current_mode == "light")
        font = FONT_FAMILY

        self.tile_widget.set_mode(is_light)

        if is_light:
            card_bg = "#FFFFFF"
            card_border = "#E4E4E7"
            title_color = "#18181B"
            top_title_color = "#71717A"
            close_btn_color = "#71717A"
            close_btn_hover = "#F4F4F5"
            desc_color = "#71717A"
            sec_btn_bg = "#F4F4F5"
            sec_btn_border = "#E4E4E7"
            sec_btn_color = "#18181B"
            sec_btn_hover = "#E4E4E7"
            prog_bg = "rgba(0, 0, 0, 0.08)"
            prog_border = "#E4E4E7"
        else:
            card_bg = "rgba(28, 29, 31, 0.96)"
            card_border = "rgba(255, 255, 255, 0.12)"
            title_color = "#F5F5F5"
            top_title_color = "#9CA3AF"
            close_btn_color = "#9CA3AF"
            close_btn_hover = "rgba(255, 255, 255, 0.08)"
            desc_color = "#8B929A"
            sec_btn_bg = "rgba(255, 255, 255, 0.05)"
            sec_btn_border = "rgba(255, 255, 255, 0.10)"
            sec_btn_color = "#A1A1AA"
            sec_btn_hover = "rgba(255, 255, 255, 0.10)"
            prog_bg = "rgba(0, 0, 0, 0.4)"
            prog_border = "rgba(255, 255, 255, 0.18)"

        self.card.setStyleSheet(f"""
            QWidget#updateCard {{
                background-color: {card_bg};
                border: 1.5px solid {card_border};
                border-radius: 22px;
            }}
            QLabel {{
                font-family: "{font}";
            }}
            QProgressBar {{
                border: 1px solid {prog_border};
                border-radius: 8px;
                background-color: {prog_bg};
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
            }}
            QProgressBar::chunk {{
                background-color: {palette.solid_bg};
                border-radius: 7px;
            }}
        """)

        self.top_title.setStyleSheet(f"color: {top_title_color}; font-weight: 500; font-family: '{font}';")
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 13px;
                font-size: 12px;
                font-weight: bold;
                color: {close_btn_color};
            }}
            QPushButton:hover {{
                background-color: {close_btn_hover};
                color: {title_color};
            }}
        """)

        self.main_title.setStyleSheet(f"color: {title_color}; letter-spacing: -0.01em; font-family: '{font}';")
        self.desc_lbl.setStyleSheet(f"color: {desc_color}; font-family: '{font}';")

        if not self._has_error:
            self.badge_lbl.setStyleSheet(f"color: {palette.text}; font-weight: bold; font-family: '{font}';")
        else:
            self.badge_lbl.setStyleSheet(f"color: #F87171; font-weight: bold; font-family: '{font}';")

        self.sec_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {sec_btn_bg};
                border: 1px solid {sec_btn_border};
                border-radius: 11px;
                color: {sec_btn_color};
                font-family: '{font}', sans-serif;
                font-size: 11.5px;
                font-weight: 600;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background-color: {sec_btn_hover};
                color: {title_color};
            }}
        """)

        if self._has_update:
            self.prim_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {palette.solid_bg};
                    color: {palette.solid_text};
                    border: 1px solid {palette.border};
                    border-radius: 11px;
                    font-family: '{font}', sans-serif;
                    font-size: 12px;
                    font-weight: 700;
                    padding: 0 18px;
                }}
                QPushButton:hover {{
                    background-color: {palette.primary};
                }}
            """)
        else:
            self.prim_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {palette.soft_bg};
                    color: {palette.cta_text};
                    border: 1.5px solid {palette.border};
                    border-radius: 11px;
                    font-family: '{font}', sans-serif;
                    font-size: 12px;
                    font-weight: 700;
                    padding: 0 18px;
                }}
                QPushButton:hover {{
                    background-color: {palette.soft_bg_hover};
                }}
            """)

    def _start_check(self):
        self._checking = True
        self.main_title.setText("Buscando actualizaciones…")
        self.badge_lbl.setText("Conectando con GitHub Releases...")
        self.badge_lbl.setStyleSheet("color: #9CA3AF;")
        self.desc_lbl.setText("Comprobando si hay nuevas versiones disponibles.")
        self.sec_btn.setEnabled(False)

        self._check_thread = CheckUpdateThread(self)
        self._check_thread.finished_check.connect(self._on_check_finished)
        self._check_thread.error_occurred.connect(self._on_check_error)
        self._check_thread.start()

    def _recheck(self):
        if self._checking:
            return
        self._start_check()

    def _on_check_finished(self, has_update: bool, tag: str, url: str, notes: str, size: int):
        self._checking = False
        self._has_error = False
        self.sec_btn.setEnabled(True)

        if has_update and url:
            self._has_update = True
            self._download_url = url
            self._new_version = tag
            self.main_title.setText(f"¡Nueva versión {tag} disponible!")
            
            size_mb = size / (1024 * 1024) if size > 0 else 0
            size_txt = f" ({size_mb:.1f} MB)" if size_mb > 0 else ""
            self.badge_lbl.setText(f"Tu versión: v{CURRENT_VERSION}  ➔  Nueva: {tag}{size_txt}")
            self.desc_lbl.setText("La actualización se descargará e instalará automáticamente.")
            
            self.sec_btn.setText("Más tarde")
            self.prim_btn.setText("🚀 Actualizar ahora")
            self._apply_theme()
            try:
                self.prim_btn.clicked.disconnect()
            except Exception:
                pass
            self.prim_btn.clicked.connect(self._start_download)
        else:
            self._has_update = False
            self.main_title.setText("Lime Radial está actualizado")
            self.badge_lbl.setText(f"✓ Ya tienes la versión más reciente (v{CURRENT_VERSION})")
            self.desc_lbl.setText("No se requieren actualizaciones en este momento.")
            
            self.sec_btn.setText("🔄 Comprobar")
            self.prim_btn.setText("Entendido")
            self._apply_theme()
            try:
                self.prim_btn.clicked.disconnect()
            except Exception:
                pass
            self.prim_btn.clicked.connect(self.accept)

    def _on_check_error(self, err_msg: str):
        self._checking = False
        self._has_error = True
        self.sec_btn.setEnabled(True)
        self.main_title.setText("Error de conexión")
        self.badge_lbl.setText("⚠️ No se pudo comprobar actualizaciones")
        self.desc_lbl.setText("Verifica tu conexión a Internet e inténtalo de nuevo.")
        self.sec_btn.setText("🔄 Reintentar")
        self._apply_theme()

    def _cleanup(self):
        if hasattr(self, "theme_mgr"):
            self.theme_mgr.remove_listener(self._apply_theme)

    def accept(self):
        self._cleanup()
        super().accept()

    def reject(self):
        self._cleanup()
        super().reject()

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)

    def _start_download(self):
        if not self._download_url:
            return

        self.prim_btn.setEnabled(False)
        self.sec_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.main_title.setText("Descargando actualización…")
        self.desc_lbl.setText("Espere unos segundos mientras se prepara el instalador...")

        self._download_thread = DownloadUpdateThread(self._download_url, self)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.finished.connect(self._on_download_finished)
        self._download_thread.error.connect(self._on_check_error)
        self._download_thread.start()

    def _on_download_progress(self, percent: int, downloaded: int, total: int):
        self.progress_bar.setValue(percent)
        dl_mb = downloaded / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        self.badge_lbl.setText(f"{percent}% completado ({dl_mb:.1f} MB / {tot_mb:.1f} MB)")

    def _on_download_finished(self, installer_path: str):
        self.main_title.setText("¡Descarga completa!")
        self.badge_lbl.setText("Instalando y reiniciando Lime Radial...")
        self.desc_lbl.setText("La aplicación se actualizará automáticamente en unos instantes.")
        self.progress_bar.setValue(100)

        # Ejecutar el instalador silenciosamente y relanzar LimeRadial
        try:
            target_exe = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "LimeRadial" / "LimeRadial.exe"
            if not target_exe.exists():
                target_exe = Path(sys.executable)

            cmd = f'start /wait "" "{installer_path}" /SILENT & start "" "{target_exe}"'
            subprocess.Popen(f"cmd /c {cmd}", shell=True)
            
            QTimer.singleShot(600, QApplication.quit)
        except Exception as e:
            self.desc_lbl.setText(f"Error al iniciar instalador: {e}")
            self.prim_btn.setEnabled(True)
            self.close_btn.setEnabled(True)


def check_for_updates(parent=None):
    """Abre el diálogo de comprobación de actualizaciones."""
    dlg = UpdateDialog(parent)
    dlg.exec()
