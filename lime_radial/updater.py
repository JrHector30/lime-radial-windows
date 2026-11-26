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

CURRENT_VERSION = "1.1.4"
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Resplandor suave de fondo
        glow = QRadialGradient(32, 32, 32)
        glow.setColorAt(0.0, QColor(250, 204, 21, 35))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), glow)

        # Mosaico de vidrio
        rect = QRectF(4, 4, 56, 56)
        painter.setBrush(QColor(255, 255, 255, 12))
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
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

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        card = QWidget(self)
        card.setObjectName("updateCard")
        card.setStyleSheet(f"""
            QWidget#updateCard {{
                background-color: rgba(28, 29, 31, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 22px;
            }}
            QLabel {{
                color: #F5F5F5;
                font-family: "{FONT_FAMILY}";
            }}
            QProgressBar {{
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 8px;
                background-color: rgba(0, 0, 0, 0.4);
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
            }}
            QProgressBar::chunk {{
                background-color: #84CC16;
                border-radius: 7px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 20)
        card_layout.setSpacing(10)

        # 1. Barra superior: Título a la izquierda, botón circular de cierre a la derecha
        top_bar = QHBoxLayout()
        top_title = QLabel("Buscar Actualizaciones")
        top_title.setFont(QFont(FONT_FAMILY, 10))
        top_title.setStyleSheet("color: #9CA3AF; font-weight: 500;")

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(26, 26)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 13px;
                font-size: 12px;
                font-weight: bold;
                color: #9CA3AF;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
            }
        """)
        self.close_btn.clicked.connect(self.accept)

        top_bar.addWidget(top_title)
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
        self.main_title.setStyleSheet("color: #F5F5F5; letter-spacing: -0.01em;")
        card_layout.addWidget(self.main_title)

        # 4. Badge de estado (Check verde con versión)
        self.badge_lbl = QLabel(f"✓ Versión actual instalada: v{CURRENT_VERSION}")
        self.badge_lbl.setAlignment(Qt.AlignCenter)
        self.badge_lbl.setFont(QFont(FONT_FAMILY, 9, QFont.DemiBold))
        self.badge_lbl.setStyleSheet("color: #A3E635;")
        self.badge_lbl.setWordWrap(True)
        card_layout.addWidget(self.badge_lbl)

        # 5. Subtítulo / Descripción
        self.desc_lbl = QLabel("Consultando el servidor oficial de GitHub Releases...")
        self.desc_lbl.setAlignment(Qt.AlignCenter)
        self.desc_lbl.setFont(QFont(FONT_FAMILY, 9))
        self.desc_lbl.setStyleSheet("color: #8B929A;")
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

        # Botón secundario "Comprobar de nuevo" / "Más tarde"
        self.sec_btn = QPushButton("🔄 Comprobar")
        self.sec_btn.setFixedHeight(36)
        self.sec_btn.setCursor(Qt.PointingHandCursor)
        self.sec_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 11px;
                color: #A1A1AA;
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 11.5px;
                font-weight: 600;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.10);
                color: #FFFFFF;
            }
        """)
        self.sec_btn.clicked.connect(self._recheck)

        # Botón primario "Entendido" / "Actualizar ahora"
        self.prim_btn = QPushButton("Entendido")
        self.prim_btn.setFixedHeight(36)
        self.prim_btn.setCursor(Qt.PointingHandCursor)
        self.prim_btn.setStyleSheet("""
            QPushButton {
                background-color: #F3F4F6;
                color: #141517;
                border: none;
                border-radius: 11px;
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 12px;
                font-weight: 700;
                padding: 0 18px;
            }
            QPushButton:hover {
                background-color: #FFFFFF;
            }
        """)
        self.prim_btn.clicked.connect(self.accept)

        self.btn_layout.addWidget(self.sec_btn)
        self.btn_layout.addWidget(self.prim_btn)
        card_layout.addLayout(self.btn_layout)

        root.addWidget(card)

        # Disparar verificación inicial
        self._start_check()

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
        self.sec_btn.setEnabled(True)

        if has_update and url:
            self._download_url = url
            self._new_version = tag
            self.main_title.setText(f"¡Nueva versión {tag} disponible!")
            
            size_mb = size / (1024 * 1024) if size > 0 else 0
            size_txt = f" ({size_mb:.1f} MB)" if size_mb > 0 else ""
            self.badge_lbl.setText(f"Tu versión: v{CURRENT_VERSION}  ➔  Nueva: {tag}{size_txt}")
            self.badge_lbl.setStyleSheet("color: #A3E635; font-weight: bold;")
            self.desc_lbl.setText("La actualización se descargará e instalará automáticamente.")
            
            self.sec_btn.setText("Más tarde")
            self.prim_btn.setText("🚀 Actualizar ahora")
            self.prim_btn.setStyleSheet("""
                QPushButton {
                    background-color: #84CC16;
                    color: #1A202C;
                    border: 1px solid #A3E635;
                    border-radius: 11px;
                    font-size: 12px;
                    font-weight: 700;
                    padding: 0 18px;
                }
                QPushButton:hover {
                    background-color: #A3E635;
                }
            """)
            self.prim_btn.clicked.disconnect()
            self.prim_btn.clicked.connect(self._start_download)
        else:
            self.main_title.setText("Lime Radial está actualizado")
            self.badge_lbl.setText(f"✓ Ya tienes la versión más reciente (v{CURRENT_VERSION})")
            self.badge_lbl.setStyleSheet("color: #A3E635; font-weight: bold;")
            self.desc_lbl.setText("No se requieren actualizaciones en este momento.")
            
            self.sec_btn.setText("🔄 Comprobar")
            self.prim_btn.setText("Entendido")
            self.prim_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F3F4F6;
                    color: #141517;
                    border: none;
                    border-radius: 11px;
                    font-size: 12px;
                    font-weight: 700;
                    padding: 0 18px;
                }
                QPushButton:hover {
                    background-color: #FFFFFF;
                }
            """)
            try:
                self.prim_btn.clicked.disconnect()
            except Exception:
                pass
            self.prim_btn.clicked.connect(self.accept)

    def _on_check_error(self, err_msg: str):
        self._checking = False
        self.sec_btn.setEnabled(True)
        self.main_title.setText("Error de conexión")
        self.badge_lbl.setText("⚠️ No se pudo comprobar actualizaciones")
        self.badge_lbl.setStyleSheet("color: #F87171;")
        self.desc_lbl.setText("Verifica tu conexión a Internet e inténtalo de nuevo.")
        self.sec_btn.setText("🔄 Reintentar")

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
