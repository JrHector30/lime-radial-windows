"""
Módulo de actualización automática para Lime Radial Windows.
Permite verificar la última versión en GitHub Releases, descargar el instalador
y actualizar automáticamente la aplicación en segundo plano.
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

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .icons import FONT_FAMILY

CURRENT_VERSION = "1.1.3"
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


class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lime Radial — Actualizaciones")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(460, 360)

        self._download_url = ""
        self._new_version = ""

        # Layout raíz
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        card = QWidget(self)
        card.setObjectName("updateCard")
        card.setStyleSheet(f"""
            QWidget#updateCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(36, 32, 28, 0.96),
                    stop:1 rgba(22, 20, 18, 0.98));
                border: 1.5px solid rgba(255, 255, 255, 0.22);
                border-radius: 24px;
            }}
            QLabel {{
                color: #FFFFFF;
                font-family: "{FONT_FAMILY}";
            }}
            QPushButton {{
                font-family: "{FONT_FAMILY}";
                font-weight: bold;
                border-radius: 10px;
                padding: 8px 18px;
                background-color: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.25);
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.25);
            }}
            QProgressBar {{
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                background-color: rgba(0, 0, 0, 0.35);
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

        self.card_layout = QVBoxLayout(card)
        self.card_layout.setContentsMargins(24, 20, 24, 20)
        self.card_layout.setSpacing(12)

        # Barra superior con botón de cerrar
        top_bar = QHBoxLayout()
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.22);
            }
        """)
        self.close_btn.clicked.connect(self.accept)

        self.title_lbl = QLabel("Buscar Actualizaciones")
        self.title_lbl.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
        self.title_lbl.setAlignment(Qt.AlignCenter)

        top_bar.addWidget(self.close_btn)
        top_bar.addWidget(self.title_lbl, 1)
        top_bar.addSpacing(28)
        self.card_layout.addLayout(top_bar)

        # Icono central
        self.icon_lbl = QLabel("🔄")
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 40px; margin-top: 6px;")
        self.card_layout.addWidget(self.icon_lbl)

        # Mensaje de estado
        self.status_lbl = QLabel("Comprobando actualizaciones en GitHub...")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        self.status_lbl.setWordWrap(True)
        self.card_layout.addWidget(self.status_lbl)

        # Detalles
        self.detail_lbl = QLabel(f"Versión actual instalada: v{CURRENT_VERSION}")
        self.detail_lbl.setAlignment(Qt.AlignCenter)
        self.detail_lbl.setFont(QFont(FONT_FAMILY, 9))
        self.detail_lbl.setStyleSheet("color: #84CC16; font-weight: bold;")
        self.detail_lbl.setWordWrap(True)
        self.card_layout.addWidget(self.detail_lbl)

        # Barra de progreso (oculta inicialmente)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setVisible(False)
        self.card_layout.addWidget(self.progress_bar)

        # Botones inferiores
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(12)

        self.action_btn = QPushButton("Aceptar")
        self.action_btn.setVisible(False)
        self.action_btn.clicked.connect(self.accept)

        self.update_btn = QPushButton("🚀 Actualizar ahora")
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #84CC16;
                color: #1A202C;
                border: 1px solid #A3E635;
                font-size: 12px;
                font-weight: bold;
                border-radius: 10px;
                padding: 9px 18px;
            }
            QPushButton:hover {
                background-color: #A3E635;
            }
        """)
        self.update_btn.setVisible(False)
        self.update_btn.clicked.connect(self._start_download)

        self.btn_layout.addWidget(self.action_btn)
        self.btn_layout.addWidget(self.update_btn)
        self.card_layout.addLayout(self.btn_layout)

        root.addWidget(card)

        # Iniciar verificación en hilo secundario
        self._check_thread = CheckUpdateThread(self)
        self._check_thread.finished_check.connect(self._on_check_finished)
        self._check_thread.error_occurred.connect(self._on_check_error)
        self._check_thread.start()

    def _on_check_finished(self, has_update: bool, tag: str, url: str, notes: str, size: int):
        if has_update and url:
            self._download_url = url
            self._new_version = tag
            self.icon_lbl.setText("🚀")
            self.status_lbl.setText(f"¡Nueva versión {tag} disponible!")
            
            size_mb = size / (1024 * 1024) if size > 0 else 0
            size_txt = f" ({size_mb:.1f} MB)" if size_mb > 0 else ""
            self.detail_lbl.setText(f"Tu versión: v{CURRENT_VERSION}  ➔  Nueva: {tag}{size_txt}\nLa actualización se descargará e instalará automáticamente.")
            
            self.action_btn.setText("Más tarde")
            self.action_btn.setVisible(True)
            self.update_btn.setVisible(True)
        else:
            self.icon_lbl.setText("🍋")
            self.status_lbl.setText("Lime Radial está actualizado")
            self.detail_lbl.setText(f"Ya tienes la versión más reciente (v{CURRENT_VERSION}).\nNo se requieren actualizaciones en este momento.")
            self.action_btn.setText("Entendido")
            self.action_btn.setVisible(True)
            self.update_btn.setVisible(False)

    def _on_check_error(self, err_msg: str):
        self.icon_lbl.setText("⚠️")
        self.status_lbl.setText("No se pudo comprobar actualizaciones")
        self.detail_lbl.setText("Verifica tu conexión a Internet e inténtalo de nuevo más tarde.")
        self.action_btn.setText("Cerrar")
        self.action_btn.setVisible(True)
        self.update_btn.setVisible(False)

    def _start_download(self):
        if not self._download_url:
            return

        self.update_btn.setEnabled(False)
        self.action_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_lbl.setText("Descargando actualización...")
        self.detail_lbl.setText("Por favor espera unos segundos...")

        self._download_thread = DownloadUpdateThread(self._download_url, self)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.finished.connect(self._on_download_finished)
        self._download_thread.error.connect(self._on_check_error)
        self._download_thread.start()

    def _on_download_progress(self, percent: int, downloaded: int, total: int):
        self.progress_bar.setValue(percent)
        dl_mb = downloaded / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        self.detail_lbl.setText(f"{percent}% completado ({dl_mb:.1f} MB / {tot_mb:.1f} MB)")

    def _on_download_finished(self, installer_path: str):
        self.status_lbl.setText("¡Descarga completa!")
        self.detail_lbl.setText("Aplicando actualización y reiniciando Lime Radial...")
        self.progress_bar.setValue(100)

        # Ejecutar el instalador y cerrar la app actual
        try:
            # En Windows: lanzar instalador con /SILENT y reabrir LimeRadial
            target_exe = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "LimeRadial" / "LimeRadial.exe"
            if not target_exe.exists():
                target_exe = Path(sys.executable)

            # Comando: esperar que instale silenciosamente y relanzar LimeRadial
            cmd = f'start /wait "" "{installer_path}" /SILENT & start "" "{target_exe}"'
            subprocess.Popen(f"cmd /c {cmd}", shell=True)
            
            # Cerrar la aplicación actual tras 500 ms
            from PySide6.QtCore import QTimer
            QTimer.singleShot(600, QApplication.quit)
        except Exception as e:
            self.detail_lbl.setText(f"Error al iniciar instalador: {e}")
            self.action_btn.setEnabled(True)
            self.close_btn.setEnabled(True)


def check_for_updates(parent=None):
    """Abre el diálogo de comprobación de actualizaciones."""
    dlg = UpdateDialog(parent)
    dlg.exec()
