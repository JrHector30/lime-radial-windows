"""
Diálogo "About / Acerca de" para Lime Radial Windows.
Incluye información de versión, licencia, créditos a herramientas de terceros
y descargo de responsabilidad (Disclaimer) formal.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .icons import FONT_FAMILY
from .themes import ThemeManager


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Lime Radial")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(520, 620)

        self._drag_pos = None
        self.theme_mgr = ThemeManager.get_instance()
        self.theme_mgr.add_listener(self._apply_theme)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)

        self.card = QWidget(self)
        self.card.setObjectName("aboutCard")
        root.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        # Barra superior con botón circular de cierre
        top_bar = QHBoxLayout()
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.clicked.connect(self.accept)

        self.title_lbl = QLabel("Acerca de / About")
        self.title_lbl.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
        self.title_lbl.setAlignment(Qt.AlignCenter)

        top_bar.addWidget(self.close_btn)
        top_bar.addWidget(self.title_lbl, 1)
        top_bar.addSpacing(30)
        card_layout.addLayout(top_bar)

        # Encabezado con Icono y Nombre
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(4)

        self.logo_label = QLabel("🍋")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet("font-size: 42px; margin-bottom: 4px;")
        header_layout.addWidget(self.logo_label)

        self.app_name = QLabel("Lime Radial")
        self.app_name.setAlignment(Qt.AlignCenter)
        self.app_name.setFont(QFont(FONT_FAMILY, 17, QFont.Bold))
        header_layout.addWidget(self.app_name)

        self.version_label = QLabel("lime-radial-windows • v1.1.8 (Open Source)")
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setFont(QFont(FONT_FAMILY, 9))
        header_layout.addWidget(self.version_label)

        card_layout.addLayout(header_layout)

        # Texto informativo con créditos y descargo de responsabilidad
        self.info_browser = QTextBrowser()
        self.info_browser.setOpenExternalLinks(True)
        card_layout.addWidget(self.info_browser, 1)

        # Botón inferior Aceptar
        bot_bar = QHBoxLayout()
        self.ok_btn = QPushButton("Cerrar")
        self.ok_btn.setFixedWidth(110)
        self.ok_btn.setFixedHeight(36)
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.clicked.connect(self.accept)
        bot_bar.addStretch()
        bot_bar.addWidget(self.ok_btn)
        bot_bar.addStretch()
        card_layout.addLayout(bot_bar)

        self._apply_theme()

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

        if is_light:
            card_bg = "#FFFFFF"
            card_border = "#E4E4E7"
            text_title = "#18181B"
            text_body = "#3F3F46"
            text_muted = "#71717A"
            close_btn_bg = "#F4F4F5"
            close_btn_color = "#71717A"
            close_btn_hover = "#E4E4E7"
            box_bg = "#F4F4F5"
            box_text = "#27272A"
        else:
            card_bg = "rgba(22, 22, 24, 0.98)"
            card_border = "rgba(255, 255, 255, 0.15)"
            text_title = "#FFFFFF"
            text_body = "#D1D5DB"
            text_muted = "#9CA3AF"
            close_btn_bg = "rgba(255, 255, 255, 0.10)"
            close_btn_color = "#FFFFFF"
            close_btn_hover = "rgba(255, 255, 255, 0.20)"
            box_bg = "rgba(255, 255, 255, 0.06)"
            box_text = "#E5E7EB"

        self.card.setStyleSheet(f"""
            QWidget#aboutCard {{
                background-color: {card_bg};
                border: 1.5px solid {card_border};
                border-radius: 24px;
            }}
            QLabel {{
                font-family: "{font}";
            }}
            QScrollBar:vertical {{
                width: 0px;
            }}
        """)

        self.title_lbl.setStyleSheet(f"color: {text_title}; font-family: '{font}';")
        self.app_name.setStyleSheet(f"color: {text_title}; font-family: '{font}';")
        self.version_label.setStyleSheet(f"color: {palette.text}; font-weight: bold; font-family: '{font}';")

        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {close_btn_bg};
                border: 1px solid {card_border};
                border-radius: 15px;
                font-size: 13px;
                font-weight: bold;
                color: {close_btn_color};
            }}
            QPushButton:hover {{
                background-color: {close_btn_hover};
            }}
        """)

        html_content = f"""
        <div style="font-family: '{font}', sans-serif; color: {text_body}; font-size: 12px; line-height: 1.5;">
            <p><b>Lime Radial</b> es una utilidad de productividad de código abierto para Windows diseñada para la manipulación y conversión rápida de archivos mediante un menú radial con interacción Shift + Arrastre.</p>
            
            <p style="margin-top: 10px;"><b>Licencia:</b> Distribuido bajo la Licencia MIT.</p>
            
            <p style="margin-top: 10px;"><b>Créditos a Proyectos de Terceros:</b></p>
            <ul style="margin-top: 4px; padding-left: 18px; color: {text_muted};">
                <li><b>PySide6 (Qt)</b> — Interfaz gráfica y motor vectorial QPainter.</li>
                <li><b>FFmpeg</b> (vía imageio-ffmpeg) — Procesamiento de audio y video.</li>
                <li><b>Pillow & Pillow-HEIF</b> — Conversión de imágenes y soporte HEIC.</li>
                <li><b>PyMuPDF</b> — Renderizado y extracción de documentos PDF.</li>
                <li><b>python-docx, python-pptx & openpyxl</b> — Soporte de documentos Office.</li>
                <li><b>Plus Jakarta Sans</b> — Tipografía (Licencia SIL Open Font).</li>
            </ul>

            <div style="margin-top: 14px; padding: 10px 12px; background-color: {box_bg}; border-left: 3px solid {palette.border}; border-radius: 4px; color: {box_text}; font-size: 11px;">
                <b>Disclaimer:</b> This project is an independent open-source utility for Windows and is not affiliated, associated, authorized, endorsed by, or in any way officially connected with Leap Studio or the original Tangerine app for macOS.
            </div>
        </div>
        """
        self.info_browser.setStyleSheet(f"background: transparent; border: none; font-family: '{font}';")
        self.info_browser.setHtml(html_content)

        self.ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {palette.soft_bg};
                color: {palette.cta_text};
                font-weight: bold;
                border: 1.5px solid {palette.border};
                padding: 8px 16px;
                border-radius: 9px;
                font-family: '{font}';
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {palette.soft_bg_hover};
            }}
            QPushButton:pressed {{
                background-color: {palette.solid_bg};
                color: {palette.solid_text};
            }}
        """)

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
