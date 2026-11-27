"""
Ventana modal interactiva de Aplanar PDF (Escaneado en tiempo real) para Lime Radial Windows.
Alineada 100% con FlattenPdfScanModal.tsx y la referencia visual:
- Comparativa en vivo: Antes (PDF plano) vs Después (Vista previa escaneada)
- Configuración de escaneo: Espacio de color (Color, Escala de Grises, Blanco y Negro) y Borde
- 8 Sliders en tiempo real: Rotar, Varianza de rotación, Brillo, Contraste, Desenfoque, Ruido, Amarillento y Resolución
- Configuración de papel: A4 y Carta
- Miniaturas de página y paginación
- Botón "Generar PDF escaneado" y botón circular de cierre (×)
"""
from __future__ import annotations

import io
import math
import os
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .convert import (
    PPTX_SUPPORTED,
    PYMUPDF_SUPPORTED,
    ensure_pdf_from_any,
    fitz,
)
from .icons import FONT_FAMILY
from .themes import ThemeAccentPalette, ThemeManager, get_theme_accent_palette


def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    rgb = pil_img.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimg = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)


@dataclass
class ScanSettings:
    color_space: str = "color"  # 'color' | 'grayscale' | 'bw'
    border: bool = True
    rotate: float = -1.4
    rotation_variance: float = 0.9
    brightness: int = 101
    contrast: int = 99
    blur: int = 70
    noise: int = 56
    yellowing: int = 3
    resolution: int = 140
    paper_size: str = "a4"  # 'a4' | 'letter'


def draw_icon_path(painter: QPainter, icon_name: str, cx: float, cy: float, size: float, color: QColor):
    """Dibuja iconos vectoriales nítidos con trazo elegante."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    hs = size / 2.0

    if icon_name == "sliders":
        # Líneas horizontales con nudos
        painter.drawLine(QPointF(cx - hs, cy - 4), QPointF(cx + hs, cy - 4))
        painter.drawEllipse(QPointF(cx - 2, cy - 4), 2.5, 2.5)
        painter.drawLine(QPointF(cx - hs, cy + 4), QPointF(cx + hs, cy + 4))
        painter.drawEllipse(QPointF(cx + 2, cy + 4), 2.5, 2.5)

    elif icon_name == "rotate_ccw":
        # Flecha circular de reinicio
        path = QPainterPath()
        rect = QRectF(cx - hs + 1, cy - hs + 1, size - 2, size - 2)
        path.arcMoveTo(rect, 40)
        path.arcTo(rect, 40, 270)
        painter.drawPath(path)
        # Punta de flecha
        arrow = QPainterPath()
        p_tip = QPointF(cx - 1, cy - hs + 1)
        arrow.moveTo(p_tip.x() - 3, p_tip.y() - 1)
        arrow.lineTo(p_tip)
        arrow.lineTo(p_tip.x() - 3, p_tip.y() + 4)
        painter.drawPath(arrow)

    elif icon_name == "close":
        # Cruz de cierre
        d = hs * 0.65
        painter.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))
        painter.drawLine(QPointF(cx + d, cy - d), QPointF(cx - d, cy + d))

    elif icon_name == "paperclip":
        # Clip
        p = QPainterPath()
        p.moveTo(cx - 3, cy + 4)
        p.lineTo(cx - 3, cy - 2)
        p.arcTo(QRectF(cx - 3, cy - 6, 6, 6), 180, -180)
        p.lineTo(cx + 3, cy + 3)
        p.arcTo(QRectF(cx - 5, cy + 1, 8, 6), 0, -180)
        p.lineTo(cx - 5, cy - 3)
        painter.drawPath(p)

    elif icon_name == "chevron_down":
        d = hs * 0.5
        painter.drawLine(QPointF(cx - d, cy - 2), QPointF(cx, cy + 2))
        painter.drawLine(QPointF(cx, cy + 2), QPointF(cx + d, cy - 2))

    elif icon_name == "chevron_up":
        d = hs * 0.5
        painter.drawLine(QPointF(cx - d, cy + 2), QPointF(cx, cy - 2))
        painter.drawLine(QPointF(cx, cy - 2), QPointF(cx + d, cy + 2))

    elif icon_name == "chevron_left":
        d = hs * 0.5
        painter.drawLine(QPointF(cx + 2, cy - d), QPointF(cx - 2, cy))
        painter.drawLine(QPointF(cx - 2, cy), QPointF(cx + 2, cy + d))

    elif icon_name == "chevron_right":
        d = hs * 0.5
        painter.drawLine(QPointF(cx - 2, cy - d), QPointF(cx + 2, cy))
        painter.drawLine(QPointF(cx + 2, cy), QPointF(cx - 2, cy + d))

    elif icon_name == "file_check":
        # Documento con checkmark
        rect = QRectF(cx - hs + 2, cy - hs + 1, size - 4, size - 2)
        painter.drawRoundedRect(rect, 2, 2)
        # Checkmark
        p = QPainterPath()
        p.moveTo(cx - 3, cy)
        p.lineTo(cx - 1, cy + 3)
        p.lineTo(cx + 4, cy - 2)
        painter.drawPath(p)

    painter.restore()


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked=True, parent=None, active_color: str = "#84CC16", is_light: bool = False):
        super().__init__(parent)
        self._checked = checked
        self._active_color = QColor(active_color)
        self._is_light = is_light
        self.setFixedSize(38, 21)
        self.setCursor(Qt.PointingHandCursor)

    def set_theme(self, active_color: str, is_light: bool = False):
        self._active_color = QColor(active_color)
        self._is_light = is_light
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        off_col = QColor("#d4d4d8") if self._is_light else QColor("#3f3f46")
        bg = self._active_color if self._checked else off_col
        p.setBrush(bg)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 38, 21, 10.5, 10.5)

        thumb_x = 19 if self._checked else 3
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(thumb_x, 2.5, 16, 16)
        p.end()


class SliderRow(QWidget):
    valueChanged = Signal(float)

    def __init__(
        self,
        label: str,
        value: float,
        min_val: float,
        max_val: float,
        step: float,
        unit: str = "",
        is_float: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.label_str = label
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.unit = unit
        self.is_float = is_float
        self._value = value

        self._multiplier = 10.0 if is_float else 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.lbl_title = QLabel(label)
        self.lbl_title.setStyleSheet(f"color: #d4d4d8; font-size: 12px; font-weight: normal; font-family: '{FONT_FAMILY}';")
        self.lbl_value = QLabel()
        self.lbl_value.setStyleSheet("color: #a1a1aa; font-family: monospace; font-size: 11.5px;")
        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(self.lbl_value)
        layout.addLayout(header)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(min_val * self._multiplier), int(max_val * self._multiplier))
        self.slider.setValue(int(value * self._multiplier))
        self.slider.valueChanged.connect(self._on_slider_change)
        layout.addWidget(self.slider)

        self._update_display(value)

    def set_theme(self, primary_color: str, border_color: str, is_light: bool = False):
        title_color = "#3f3f46" if is_light else "#d4d4d8"
        value_color = "#71717a" if is_light else "#a1a1aa"
        groove_bg = "#e4e4e7" if is_light else "#36373b"
        handle_bg = "#ffffff" if is_light else "#f8fafc"
        handle_border = "rgba(0, 0, 0, 0.20)" if is_light else "rgba(0, 0, 0, 0.25)"

        self.lbl_title.setStyleSheet(f"color: {title_color}; font-size: 12px; font-weight: normal; font-family: '{FONT_FAMILY}';")
        self.lbl_value.setStyleSheet(f"color: {value_color}; font-family: monospace; font-size: 11.5px;")

        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {groove_bg};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {primary_color};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {handle_bg};
                border: 1.5px solid {handle_border};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: #ffffff;
                border: 1.5px solid {border_color};
            }}
        """)

    def _update_display(self, val: float):
        if self.is_float:
            sign = "±" if "Varianza" in self.label_str else ""
            txt = f"{sign}{val:.1f}".replace(".", ",") + f" {self.unit}".strip()
        else:
            txt = f"{int(val)} {self.unit}".strip()
        self.lbl_value.setText(txt)

    def _on_slider_change(self, int_val: int):
        val = float(int_val) / self._multiplier
        self._value = val
        self._update_display(val)
        self.valueChanged.emit(val)

    def set_value(self, val: float):
        self._value = val
        self.slider.blockSignals(True)
        self.slider.setValue(int(val * self._multiplier))
        self.slider.blockSignals(False)
        self._update_display(val)

    def value(self) -> float:
        return self._value


def render_simulated_document_page(file_name: str, page_num: int, width: int = 595, height: int = 842) -> QImage:
    """Genera una página de documento corporativo nítida idéntica al diseño de DocumentPageContent.tsx."""
    img = QImage(width, height, QImage.Format_ARGB32)
    img.fill(QColor("#FFFFFF"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)

    clean_title = Path(file_name).stem.replace("_", " ")

    if page_num == 1:
        # Cabecera corporativa
        p.setBrush(QColor("#0f766e"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(40, 42, 14, 14, 2, 2)

        p.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
        p.setPen(QColor("#0f766e"))
        p.drawText(62, 54, "NOR PERUANA DE TELECOMUNICACIONES")

        # Título principal
        p.setFont(QFont(FONT_FAMILY, 15, QFont.Bold))
        p.setPen(QColor("#111827"))
        p.drawText(QRectF(40, 75, width - 80, 50), Qt.AlignLeft | Qt.TextWordWrap, clean_title)

        # Párrafo intro
        p.setFont(QFont("Georgia", 10))
        p.setPen(QColor("#374151"))
        intro = (
            "Este documento contiene el registro operativo de transmisión diaria y la verificación "
            "de enlace de estación base correspondiente al turno programado."
        )
        p.drawText(QRectF(40, 135, width - 80, 45), Qt.AlignLeft | Qt.TextWordWrap, intro)

        # Sección 1
        p.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        p.setPen(QColor("#111827"))
        p.drawText(40, 205, "1. Parámetros de Transmisión")

        p.setFont(QFont("Georgia", 10))
        p.setPen(QColor("#374151"))
        sec1 = (
            "Se mantiene estabilidad de portadora dentro del margen nominal de operación. "
            "Los valores de potencia reflejada y relación señal/ruido permanecen conformes a la normativa técnica vigente."
        )
        p.drawText(QRectF(40, 220, width - 80, 45), Qt.AlignLeft | Qt.TextWordWrap, sec1)

        # Tabla técnica
        p.setPen(QPen(QColor("#d1d5db"), 1.0))
        p.setBrush(QColor("#f9fafb"))
        p.drawRect(40, 275, width - 80, 85)

        p.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        p.setPen(QColor("#111827"))
        p.drawText(55, 298, "Bloque Horario")
        p.drawText(220, 298, "Frecuencia")
        p.drawText(390, 298, "Estado")

        p.setPen(QPen(QColor("#e5e5e7"), 1.0))
        p.drawLine(40, 308, width - 40, 308)

        p.setFont(QFont(FONT_FAMILY, 9))
        p.setPen(QColor("#4b5563"))
        p.drawText(55, 328, "06:00 – 12:00")
        p.drawText(220, 328, "98.5 MHz")
        p.setPen(QColor("#15803d"))
        p.drawText(390, 328, "Continuo")

        p.setPen(QColor("#4b5563"))
        p.drawText(55, 348, "12:00 – 18:00")
        p.drawText(220, 348, "98.5 MHz")
        p.setPen(QColor("#15803d"))
        p.drawText(390, 348, "Continuo")

        # Sección 2
        p.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        p.setPen(QColor("#111827"))
        p.drawText(40, 395, "2. Control y Verificación Local")

        p.setFont(QFont("Georgia", 10))
        p.setPen(QColor("#374151"))
        sec2 = (
            "La lectura de telemetría fue validada por el operador de guardia sin incidencias "
            "de corte o atenuación atmosférica relevante durante la jornada."
        )
        p.drawText(QRectF(40, 410, width - 80, 45), Qt.AlignLeft | Qt.TextWordWrap, sec2)

        # Sección 3
        p.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        p.setPen(QColor("#111827"))
        p.drawText(40, 480, "3. Conformidad del Archivo")

        p.setFont(QFont("Georgia", 10))
        p.setPen(QColor("#374151"))
        sec3 = (
            "Documento listo para archivo y visado administrativo. Al generar el PDF escaneado "
            "se aplicará aplanamiento completo sobre cada página."
        )
        p.drawText(QRectF(40, 495, width - 80, 45), Qt.AlignLeft | Qt.TextWordWrap, sec3)

    else:
        # Página 2: Anexo técnico
        p.setFont(QFont(FONT_FAMILY, 9.5, QFont.Bold))
        p.setPen(QColor("#4b5563"))
        p.drawText(40, 50, "ANEXO TÉCNICO — PÁGINA 2")
        p.setFont(QFont(FONT_FAMILY, 9))
        p.setPen(QColor("#6b7280"))
        p.drawText(width - 150, 50, "REF: NPT-2026-11")

        p.setPen(QPen(QColor("#e5e7eb"), 1.0))
        p.drawLine(40, 60, width - 40, 60)

        p.setFont(QFont(FONT_FAMILY, 11.5, QFont.Bold))
        p.setPen(QColor("#111827"))
        p.drawText(40, 95, "Observaciones de Mantenimiento Preventivo")

        p.setFont(QFont("Georgia", 10))
        p.setPen(QColor("#374151"))
        sec = (
            "Durante la inspección visual del sistema radiante y líneas de transmisión "
            "no se registraron anomalías térmicas ni desajustes en los conectores coaxiales principales."
        )
        p.drawText(QRectF(40, 110, width - 80, 45), Qt.AlignLeft | Qt.TextWordWrap, sec)

        bullet1 = "• Verificación de puesta a tierra dentro de rango (< 5 Ω)."
        bullet2 = "• Banco de baterías de respaldo al 100% de carga nominal."
        bullet3 = "• Registro fotográfico y reporte horario archivados localmente."
        p.drawText(50, 180, bullet1)
        p.drawText(50, 205, bullet2)
        p.drawText(50, 230, bullet3)

        # Firmas al pie
        p.setPen(QPen(QColor("#4b5563"), 1.0))
        p.drawLine(70, 500, 230, 500)
        p.drawLine(width - 230, 500, width - 70, 500)

        p.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        p.setPen(QColor("#111827"))
        p.drawText(QRectF(50, 510, 200, 20), Qt.AlignCenter, "Responsable de Turno")
        p.drawText(QRectF(width - 250, 510, 200, 20), Qt.AlignCenter, "V°B° Jefatura Técnica")

        p.setFont(QFont(FONT_FAMILY, 8.5))
        p.setPen(QColor("#6b7280"))
        p.drawText(QRectF(50, 528, 200, 20), Qt.AlignCenter, "Operaciones Nor Peruana")
        p.drawText(QRectF(width - 250, 528, 200, 20), Qt.AlignCenter, "Control de Emisión")

    p.end()
    return img


def apply_scan_effects_to_image(
    base_pil: Image.Image,
    settings: ScanSettings,
    page_index: int = 1,
    preview_scale: float = 1.0,
) -> Image.Image:
    """Aplica la cadena completa de filtros analógicos de escáner a una imagen PIL."""
    im = base_pil.copy()

    # 1. Espacio de color
    if settings.color_space == "grayscale":
        im = ImageOps.grayscale(im).convert("RGB")
    elif settings.color_space == "bw":
        im = ImageOps.grayscale(im)
        im = ImageEnhance.Contrast(im).enhance(2.15)
        im = ImageEnhance.Brightness(im).enhance(1.06)
        im = im.point(lambda p: 255 if p > 160 else 0).convert("RGB")

    # 2. Brillo y Contraste
    if settings.brightness != 100:
        im = ImageEnhance.Brightness(im).enhance(settings.brightness / 100.0)
    if settings.contrast != 100:
        im = ImageEnhance.Contrast(im).enhance(settings.contrast / 100.0)

    # 3. Amarillento (Tinte cálido de papel envejecido)
    if settings.yellowing > 0 and settings.color_space == "color":
        alpha = min(0.42, (settings.yellowing / 100.0) * 0.36)
        tint = Image.new("RGB", im.size, (232, 198, 120))
        im = Image.blend(im, tint, alpha)

    # 4. Desenfoque / Suavizado de baja resolución
    blur_amount = (settings.blur / 100.0) * 0.75 * preview_scale
    if settings.resolution < 140:
        blur_amount += ((140 - settings.resolution) / 68.0) * 0.45 * preview_scale
    if blur_amount > 0.05:
        im = im.filter(ImageFilter.GaussianBlur(radius=blur_amount))

    # 5. Ruido de grano de papel / sensor CCD
    if settings.noise > 0:
        alpha = min(0.35, (settings.noise / 100.0) * 0.28)
        raw = os.urandom(im.width * im.height)
        noise_layer = Image.frombytes("L", im.size, raw).convert("RGB")
        im = Image.blend(im, noise_layer, alpha)

    # 6. Rotación con varianza analógica por página
    variance_sign = 1 if page_index == 1 else -1
    effective_rot = settings.rotate + variance_sign * settings.rotation_variance * 0.45

    # 7. Borde de la platina del escáner (Scanner Platen Bed)
    if settings.border:
        pad_x = int(im.width * 0.045)
        pad_y = int(im.height * 0.04)
        bed_w = im.width + pad_x * 2
        bed_h = im.height + pad_y * 2
        bed = Image.new("RGB", (bed_w, bed_h), (229, 229, 227))

        rot_im = im.rotate(effective_rot, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))
        bed.paste(rot_im, (pad_x, pad_y))

        # Viñeteado suave en los bordes
        im = bed
    else:
        im = im.rotate(effective_rot, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))

    return im


class FlattenPdfScanDialog(QDialog):
    def __init__(self, file_paths: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aplanar PDF — Vista previa de escaneo")
        # Ventana independiente común (no modal) para permitir seguir usando el PC y Lime Radial
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(False)
        self.resize(1180, 780)

        self.file_paths = [str(Path(p).resolve()) for p in file_paths if os.path.exists(p)]
        if not self.file_paths:
            self.file_paths = ["33-A. HORARIO DE TRANSMISION - NOR PERUANA.pdf"]

        self.selected_file_index = 0
        self.active_page = 1
        self.total_pages = 2
        self.show_thumbnails = True
        self.settings = ScanSettings()

        self._pdf_doc = None
        self._temp_converted_pdf = None
        self._drag_pos = None

        self.theme_mgr = ThemeManager.get_instance()
        self.theme_mgr.add_listener(self._apply_theme)

        self._load_current_document()
        self._build_ui()
        self._apply_theme()
        self._update_previews()

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

    def _load_current_document(self):
        """Carga el documento actual con PyMuPDF o prepara renderizado fiel."""
        current_path = Path(self.file_paths[self.selected_file_index])
        if self._pdf_doc:
            try:
                self._pdf_doc.close()
            except Exception:
                pass
            self._pdf_doc = None

        if self._temp_converted_pdf and os.path.exists(self._temp_converted_pdf):
            try:
                os.remove(self._temp_converted_pdf)
            except Exception:
                pass
            self._temp_converted_pdf = None

        if current_path.exists() and PYMUPDF_SUPPORTED:
            if current_path.suffix.lower() == ".pdf":
                try:
                    self._pdf_doc = fitz.open(str(current_path))
                    self.total_pages = max(1, len(self._pdf_doc))
                    return
                except Exception:
                    pass
            else:
                # Convertir temporalmente a PDF para previsualizar fielmente
                temp_pdf = Path(tempfile.gettempdir()) / f"lime_view_{uuid.uuid4().hex[:8]}.pdf"
                if ensure_pdf_from_any(current_path, temp_pdf) and temp_pdf.exists():
                    self._temp_converted_pdf = str(temp_pdf)
                    try:
                        self._pdf_doc = fitz.open(str(temp_pdf))
                        self.total_pages = max(1, len(self._pdf_doc))
                        return
                    except Exception:
                        pass

        self.total_pages = 2

    def _get_page_image(self, page_num: int, target_w: int = 595, target_h: int = 842) -> Image.Image:
        """Obtiene la imagen base de la página solicitada (del PDF real o simulada)."""
        if self._pdf_doc and 1 <= page_num <= len(self._pdf_doc):
            try:
                page = self._pdf_doc.load_page(page_num - 1)
                dpi = 110
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            except Exception:
                pass

        fname = Path(self.file_paths[self.selected_file_index]).name
        qimg = render_simulated_document_page(fname, page_num, width=target_w, height=target_h)
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        qimg.save(buf, "PNG")
        return Image.open(io.BytesIO(buf.data().data())).convert("RGB")

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        self.card = QFrame(self)
        self.card.setObjectName("scanCard")
        root.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ---------------- 1. Top Header ----------------
        self.header = QFrame(self.card)
        self.header.setFixedHeight(46)
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(16, 0, 16, 0)
        h_layout.setSpacing(10)

        self.lbl_header_icon = QLabel()
        h_layout.addWidget(self.lbl_header_icon)

        self.lbl_header_title = QLabel("Aplanar PDF — Vista previa de escaneo")
        h_layout.addWidget(self.lbl_header_title)

        if len(self.file_paths) > 1:
            self.lbl_count = QLabel(f"· {len(self.file_paths)} archivos")
            self.lbl_count.setStyleSheet("font-size: 11.5px; color: #a1a1aa; font-family: monospace;")
            h_layout.addWidget(self.lbl_count)
        else:
            self.lbl_count = None

        h_layout.addStretch()

        self.btn_reset = QPushButton(" Restablecer")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._reset_defaults)
        h_layout.addWidget(self.btn_reset)

        self.btn_close = QPushButton()
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.close)
        h_layout.addWidget(self.btn_close)

        card_layout.addWidget(self.header)

        # ---------------- 2. Main Body: Sidebar + Previews ----------------
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # === Sidebar izquierdo de controles (310px) ===
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(310)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(10)

        # Card de Información de Archivo
        self.card_file = QFrame()
        cf_layout = QVBoxLayout(self.card_file)
        cf_layout.setContentsMargins(10, 10, 10, 10)
        cf_layout.setSpacing(4)

        row_f = QHBoxLayout()
        row_f.setSpacing(6)
        self.lbl_clip = QLabel()
        pix_clip = QPixmap(14, 14)
        pix_clip.fill(Qt.transparent)
        p = QPainter(pix_clip)
        draw_icon_path(p, "paperclip", 7, 7, 12, QColor("#a1a1aa"))
        p.end()
        self.lbl_clip.setPixmap(pix_clip)
        row_f.addWidget(self.lbl_clip)

        if len(self.file_paths) > 1:
            self.combo_files = QComboBox()
            self.combo_files.addItems([Path(f).name for f in self.file_paths])
            self.combo_files.setStyleSheet(f"background: transparent; font-size: 12px; border: none; font-family: '{FONT_FAMILY}';")
            self.combo_files.currentIndexChanged.connect(self._on_file_changed)
            row_f.addWidget(self.combo_files)
        else:
            self.lbl_fname = QLabel(Path(self.file_paths[0]).name)
            self.lbl_fname.setStyleSheet(f"font-size: 12.5px; font-weight: 500; font-family: '{FONT_FAMILY}';")
            row_f.addWidget(self.lbl_fname)
        cf_layout.addLayout(row_f)

        self.lbl_fsize = QLabel(self._get_file_size_label())
        self.lbl_fsize.setStyleSheet("color: #a1a1aa; font-family: monospace; font-size: 11px; margin-left: 20px;")
        cf_layout.addWidget(self.lbl_fsize)
        side_layout.addWidget(self.card_file)

        # ScrollArea para controles de escaneo
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollBar:vertical { width: 0px; }")

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        sw_layout = QVBoxLayout(scroll_widget)
        sw_layout.setContentsMargins(0, 0, 0, 0)
        sw_layout.setSpacing(8)

        # Acordeón: Configuración de Escaneo
        self.card_scan = QFrame()
        cs_layout = QVBoxLayout(self.card_scan)
        cs_layout.setContentsMargins(12, 10, 12, 12)
        cs_layout.setSpacing(10)

        self.lbl_scan_sec = QLabel("⚙️  Configuración de escaneo")
        cs_layout.addWidget(self.lbl_scan_sec)

        # Fila: Espacio de color + Borde
        row_cb = QHBoxLayout()
        row_cb.setSpacing(10)

        v_col = QVBoxLayout()
        v_col.setSpacing(4)
        self.lbl_c_title = QLabel("Espacio de color")
        self.combo_color = QComboBox()
        self.combo_color.addItem("Color", "color")
        self.combo_color.addItem("Escala de Grises", "grayscale")
        self.combo_color.addItem("Blanco y Negro", "bw")
        self.combo_color.currentIndexChanged.connect(self._on_color_space_changed)
        v_col.addWidget(self.lbl_c_title)
        v_col.addWidget(self.combo_color)
        row_cb.addLayout(v_col)

        v_bor = QVBoxLayout()
        v_bor.setSpacing(4)
        self.lbl_b_title = QLabel("Borde")
        self.switch_border = ToggleSwitch(checked=True)
        self.switch_border.toggled.connect(self._on_border_toggled)
        v_bor.addWidget(self.lbl_b_title)
        v_bor.addWidget(self.switch_border)
        row_cb.addLayout(v_bor)

        cs_layout.addLayout(row_cb)

        # Sliders en tiempo real
        self.slider_rotate = SliderRow("Rotar", self.settings.rotate, -5.0, 5.0, 0.1, "°", is_float=True)
        self.slider_rotate.valueChanged.connect(lambda v: self._update_setting("rotate", v))
        cs_layout.addWidget(self.slider_rotate)

        self.slider_variance = SliderRow("Varianza de rotación", self.settings.rotation_variance, 0.0, 3.0, 0.1, "°", is_float=True)
        self.slider_variance.valueChanged.connect(lambda v: self._update_setting("rotation_variance", v))
        cs_layout.addWidget(self.slider_variance)

        self.slider_brightness = SliderRow("Brillo", self.settings.brightness, 50, 150, 1, "%")
        self.slider_brightness.valueChanged.connect(lambda v: self._update_setting("brightness", int(v)))
        cs_layout.addWidget(self.slider_brightness)

        self.slider_contrast = SliderRow("Contraste", self.settings.contrast, 50, 180, 1, "%")
        self.slider_contrast.valueChanged.connect(lambda v: self._update_setting("contrast", int(v)))
        cs_layout.addWidget(self.slider_contrast)

        self.slider_blur = SliderRow("Desenfoque", self.settings.blur, 0, 100, 1, "%")
        self.slider_blur.valueChanged.connect(lambda v: self._update_setting("blur", int(v)))
        cs_layout.addWidget(self.slider_blur)

        self.slider_noise = SliderRow("Ruido", self.settings.noise, 0, 100, 1, "%")
        self.slider_noise.valueChanged.connect(lambda v: self._update_setting("noise", int(v)))
        cs_layout.addWidget(self.slider_noise)

        self.slider_yellowing = SliderRow("Amarillento", self.settings.yellowing, 0, 100, 1, "%")
        self.slider_yellowing.valueChanged.connect(lambda v: self._update_setting("yellowing", int(v)))
        cs_layout.addWidget(self.slider_yellowing)

        self.slider_resolution = SliderRow("Resolución", self.settings.resolution, 72, 300, 1, "PPI")
        self.slider_resolution.valueChanged.connect(lambda v: self._update_setting("resolution", int(v)))
        cs_layout.addWidget(self.slider_resolution)

        sw_layout.addWidget(self.card_scan)

        # Acordeón: Configuración de Papel
        self.card_paper = QFrame()
        cp_layout = QVBoxLayout(self.card_paper)
        cp_layout.setContentsMargins(12, 10, 12, 10)
        cp_layout.setSpacing(8)

        self.lbl_paper_sec = QLabel("📄  Configuración de papel")
        cp_layout.addWidget(self.lbl_paper_sec)

        self.lbl_psize = QLabel("Tamaño de hoja")
        cp_layout.addWidget(self.lbl_psize)

        row_pbtns = QHBoxLayout()
        row_pbtns.setSpacing(6)
        self.btn_a4 = QPushButton("A4")
        self.btn_letter = QPushButton("Carta")
        self.btn_a4.setCheckable(True)
        self.btn_letter.setCheckable(True)
        self.btn_a4.setChecked(True)

        self.paper_group = QButtonGroup(self)
        self.paper_group.addButton(self.btn_a4)
        self.paper_group.addButton(self.btn_letter)
        self.paper_group.setExclusive(True)

        self.btn_a4.clicked.connect(lambda: self._set_paper_size("a4"))
        self.btn_letter.clicked.connect(lambda: self._set_paper_size("letter"))
        row_pbtns.addWidget(self.btn_a4)
        row_pbtns.addWidget(self.btn_letter)
        cp_layout.addLayout(row_pbtns)

        sw_layout.addWidget(self.card_paper)
        sw_layout.addStretch()

        scroll.setWidget(scroll_widget)
        side_layout.addWidget(scroll, 1)

        # Botón inferior: Generar PDF escaneado
        self.btn_generate = QPushButton("  Generar PDF escaneado")
        self.btn_generate.setFixedHeight(40)
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.clicked.connect(self._on_generate_clicked)
        side_layout.addWidget(self.btn_generate)

        body.addWidget(self.sidebar)

        # === Right Preview Area (Comparativa Antes y Después) ===
        self.right_panel = QFrame()
        rp_layout = QVBoxLayout(self.right_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.setSpacing(0)

        # Canvas central con los dos documentos
        self.center_canvas = QFrame()
        canvas_layout = QHBoxLayout(self.center_canvas)
        canvas_layout.setContentsMargins(30, 20, 30, 20)
        canvas_layout.setSpacing(30)
        canvas_layout.setAlignment(Qt.AlignCenter)

        # Columna 1: Antes (PDF plano)
        col_before = QVBoxLayout()
        col_before.setSpacing(8)
        col_before.setAlignment(Qt.AlignCenter)
        self.lbl_preview_before = QLabel("Antes (PDF plano)")
        col_before.addWidget(self.lbl_preview_before, 0, Qt.AlignCenter)

        self.view_before = QLabel()
        self.view_before.setFixedSize(330, 460)
        self.view_before.setAlignment(Qt.AlignCenter)
        self.view_before.setStyleSheet("""
            background-color: #ffffff;
            border-radius: 2px;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.65);
        """)
        col_before.addWidget(self.view_before, 0, Qt.AlignCenter)
        canvas_layout.addLayout(col_before)

        # Columna 2: Después (Vista previa escaneada)
        col_after = QVBoxLayout()
        col_after.setSpacing(8)
        col_after.setAlignment(Qt.AlignCenter)
        self.lbl_preview_after = QLabel("Después (Vista previa escaneada)")
        col_after.addWidget(self.lbl_preview_after, 0, Qt.AlignCenter)

        self.view_after = QLabel()
        self.view_after.setFixedSize(330, 460)
        self.view_after.setAlignment(Qt.AlignCenter)
        self.view_after.setStyleSheet("""
            background-color: #e5e5e3;
            border-radius: 2px;
        """)
        col_after.addWidget(self.view_after, 0, Qt.AlignCenter)
        canvas_layout.addLayout(col_after)

        rp_layout.addWidget(self.center_canvas, 1)

        # Barra inferior de Paginación y Miniaturas
        self.bottom_strip = QFrame()
        bs_layout = QVBoxLayout(self.bottom_strip)
        bs_layout.setContentsMargins(16, 8, 16, 8)
        bs_layout.setSpacing(6)

        # Fila de control de página
        row_page = QHBoxLayout()
        self.lbl_page_info = QLabel("Página 1 de 2")
        row_page.addWidget(self.lbl_page_info)
        row_page.addStretch()

        self.btn_prev_page = QPushButton()
        self.btn_prev_page.setFixedSize(28, 28)
        self.btn_prev_page.setCursor(Qt.PointingHandCursor)
        pix_pl = QPixmap(14, 14)
        pix_pl.fill(Qt.transparent)
        p = QPainter(pix_pl)
        draw_icon_path(p, "chevron_left", 7, 7, 12, QColor("#a1a1aa"))
        p.end()
        self.btn_prev_page.setIcon(pix_pl)
        self.btn_prev_page.clicked.connect(self._prev_page)
        row_page.addWidget(self.btn_prev_page)

        self.btn_next_page = QPushButton()
        self.btn_next_page.setFixedSize(28, 28)
        self.btn_next_page.setCursor(Qt.PointingHandCursor)
        pix_pr = QPixmap(14, 14)
        pix_pr.fill(Qt.transparent)
        p = QPainter(pix_pr)
        draw_icon_path(p, "chevron_right", 7, 7, 12, QColor("#a1a1aa"))
        p.end()
        self.btn_next_page.setIcon(pix_pr)
        self.btn_next_page.clicked.connect(self._next_page)
        row_page.addWidget(self.btn_next_page)

        self.lbl_sep = QLabel("|")
        row_page.addWidget(self.lbl_sep)

        self.btn_toggle_thumbs = QPushButton("Ocultar miniaturas")
        self.btn_toggle_thumbs.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_thumbs.clicked.connect(self._toggle_thumbnails)
        row_page.addWidget(self.btn_toggle_thumbs)

        bs_layout.addLayout(row_page)

        # Fila de miniaturas de página
        self.thumbs_container = QWidget()
        self.thumbs_layout = QHBoxLayout(self.thumbs_container)
        self.thumbs_layout.setContentsMargins(0, 4, 0, 4)
        self.thumbs_layout.setSpacing(10)
        self.thumbs_layout.setAlignment(Qt.AlignLeft)
        bs_layout.addWidget(self.thumbs_container)

        rp_layout.addWidget(self.bottom_strip)
        body.addWidget(self.right_panel, 1)

        card_layout.addLayout(body, 1)

    def _apply_theme(self, theme=None):
        """Aplica la paleta de acentos dinámicos y adapta superficies a modo Claro u Oscuro."""
        palette = self.theme_mgr.get_accent_palette()
        is_light = (self.theme_mgr.current_mode == "light")
        font = FONT_FAMILY

        if is_light:
            card_bg = "#FFFFFF"
            card_border = "#E4E4E7"
            header_bg = "#FFFFFF"
            header_border = "#E4E4E7"
            title_color = "#18181B"
            btn_txt = "#71717A"
            btn_hover = "#F4F4F5"
            sidebar_bg = "#F4F4F5"
            sidebar_border = "#E4E4E7"
            subcard_bg = "#FFFFFF"
            subcard_border = "#E4E4E7"
            text_primary = "#18181B"
            text_secondary = "#71717A"
            canvas_bg = "#EAECF0"
            bottom_bg = "#FFFFFF"
            bottom_border = "#E4E4E7"
            btn_page_bg = "#F4F4F5"
            btn_page_border = "#E4E4E7"
            combo_bg = "#FFFFFF"
            combo_border = "#D4D4D8"
            sep_col = "#E4E4E7"
        else:
            card_bg = "#141416"
            card_border = "rgba(255, 255, 255, 0.12)"
            header_bg = "#18181B"
            header_border = "rgba(255, 255, 255, 0.08)"
            title_color = "#F4F4F5"
            btn_txt = "#A1A1AA"
            btn_hover = "rgba(255, 255, 255, 0.08)"
            sidebar_bg = "#161619"
            sidebar_border = "rgba(255, 255, 255, 0.08)"
            subcard_bg = "#1B1B1F"
            subcard_border = "rgba(255, 255, 255, 0.08)"
            text_primary = "#F4F4F5"
            text_secondary = "#A1A1AA"
            canvas_bg = "#101012"
            bottom_bg = "#18181B"
            bottom_border = "rgba(255, 255, 255, 0.08)"
            btn_page_bg = "#222226"
            btn_page_border = "rgba(255, 255, 255, 0.08)"
            combo_bg = "#121215"
            combo_border = "rgba(255, 255, 255, 0.14)"
            sep_col = "rgba(255, 255, 255, 0.10)"

        self.card.setStyleSheet(f"""
            QFrame#scanCard {{
                background-color: {card_bg};
                border: 1.5px solid {card_border};
                border-radius: 14px;
            }}
            QLabel {{
                color: {text_primary};
                font-family: "{font}";
            }}
        """)

        self.header.setStyleSheet(f"background-color: {header_bg}; border-bottom: 1px solid {header_border};")
        self.lbl_header_title.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {title_color}; font-family: '{font}';")

        if hasattr(self, "lbl_fname"):
            self.lbl_fname.setStyleSheet(f"color: {text_primary}; font-size: 12.5px; font-weight: 500; font-family: '{font}';")

        # Icono dinámico de sliders en header
        pix_icon = QPixmap(18, 18)
        pix_icon.fill(Qt.transparent)
        p = QPainter(pix_icon)
        draw_icon_path(p, "sliders", 9, 9, 16, QColor(palette.primary))
        p.end()
        self.lbl_header_icon.setPixmap(pix_icon)

        # Botón Restablecer
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                color: {btn_txt};
                font-size: 11.5px;
                font-weight: 500;
                font-family: '{font}';
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                color: {title_color};
            }}
        """)
        pix_rst = QPixmap(14, 14)
        pix_rst.fill(Qt.transparent)
        p = QPainter(pix_rst)
        draw_icon_path(p, "rotate_ccw", 7, 7, 12, QColor(btn_txt))
        p.end()
        self.btn_reset.setIcon(pix_rst)

        # Botón Cerrar
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 7px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        pix_cls = QPixmap(16, 16)
        pix_cls.fill(Qt.transparent)
        p = QPainter(pix_cls)
        draw_icon_path(p, "close", 8, 8, 12, QColor(btn_txt))
        p.end()
        self.btn_close.setIcon(pix_cls)

        # Sidebar & inner cards
        self.sidebar.setStyleSheet(f"background-color: {sidebar_bg}; border-right: 1px solid {sidebar_border};")
        self.card_file.setStyleSheet(f"background-color: {subcard_bg}; border: 1px solid {subcard_border}; border-radius: 8px;")
        self.card_scan.setStyleSheet(f"background-color: {subcard_bg}; border: 1px solid {subcard_border}; border-radius: 8px;")
        self.card_paper.setStyleSheet(f"background-color: {subcard_bg}; border: 1px solid {subcard_border}; border-radius: 8px;")

        self.lbl_scan_sec.setStyleSheet(f"font-size: 12.5px; font-weight: bold; color: {text_primary}; margin-bottom: 2px; font-family: '{font}';")
        self.lbl_paper_sec.setStyleSheet(f"font-size: 12.5px; font-weight: bold; color: {text_primary}; font-family: '{font}';")
        self.lbl_c_title.setStyleSheet(f"font-size: 11.5px; color: {text_secondary}; font-family: '{font}';")
        self.lbl_b_title.setStyleSheet(f"font-size: 11.5px; color: {text_secondary}; font-family: '{font}';")
        self.lbl_psize.setStyleSheet(f"font-size: 11.5px; color: {text_secondary}; font-family: '{font}';")

        # Dropdown
        self.combo_color.setStyleSheet(f"""
            QComboBox {{
                background-color: {combo_bg};
                color: {text_primary};
                border: 1px solid {combo_border};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                font-family: '{font}';
            }}
            QComboBox:focus {{
                border: 1.5px solid {palette.border};
            }}
        """)

        # Interruptor Borde
        self.switch_border.set_theme(palette.primary, is_light=is_light)

        # 8 Sliders en tiempo real
        for s in (
            self.slider_rotate,
            self.slider_variance,
            self.slider_brightness,
            self.slider_contrast,
            self.slider_blur,
            self.slider_noise,
            self.slider_yellowing,
            self.slider_resolution,
        ):
            s.set_theme(palette.primary, palette.border, is_light=is_light)

        # Botones de hoja (A4 / Carta)
        pbtn_style = f"""
            QPushButton {{
                background-color: {combo_bg};
                border: 1px solid {combo_border};
                border-radius: 5px;
                padding: 5px 0;
                color: {text_secondary};
                font-size: 12px;
                font-weight: 500;
                font-family: '{font}';
            }}
            QPushButton:hover {{
                color: {text_primary};
            }}
            QPushButton:checked {{
                background-color: {palette.soft_bg};
                border: 1.5px solid {palette.border};
                color: {palette.text};
                font-weight: bold;
            }}
        """
        self.btn_a4.setStyleSheet(pbtn_style)
        self.btn_letter.setStyleSheet(pbtn_style)

        # Botón CTA Generar PDF escaneado
        self.btn_generate.setStyleSheet(f"""
            QPushButton {{
                background-color: {palette.soft_bg};
                border: 1.5px solid {palette.border};
                border-radius: 8px;
                color: {palette.cta_text};
                font-size: 13px;
                font-weight: bold;
                font-family: '{font}';
            }}
            QPushButton:hover {{
                background-color: {palette.soft_bg_hover};
            }}
            QPushButton:pressed {{
                background-color: {palette.solid_bg};
                color: {palette.solid_text};
            }}
        """)
        pix_gen = QPixmap(16, 16)
        pix_gen.fill(Qt.transparent)
        p = QPainter(pix_gen)
        draw_icon_path(p, "file_check", 8, 8, 14, QColor(palette.primary))
        p.end()
        self.btn_generate.setIcon(pix_gen)

        # Canvas central & etiquetas Antes/Después
        self.right_panel.setStyleSheet(f"background-color: {canvas_bg};")
        self.center_canvas.setStyleSheet(f"background-color: {canvas_bg};")
        self.lbl_preview_before.setStyleSheet(f"font-size: 11.5px; font-weight: 500; color: {text_secondary}; font-family: '{font}';")
        self.lbl_preview_after.setStyleSheet(f"font-size: 11.5px; font-weight: bold; color: {palette.text}; font-family: '{font}';")

        # Barra inferior
        self.bottom_strip.setStyleSheet(f"background-color: {bottom_bg}; border-top: 1px solid {bottom_border};")
        self.lbl_page_info.setStyleSheet(f"font-size: 12px; color: {text_secondary}; font-family: monospace;")
        self.btn_prev_page.setStyleSheet(f"background-color: {btn_page_bg}; border: 1px solid {btn_page_border}; border-radius: 5px;")
        self.btn_next_page.setStyleSheet(f"background-color: {btn_page_bg}; border: 1px solid {btn_page_border}; border-radius: 5px;")
        self.lbl_sep.setStyleSheet(f"color: {sep_col}; margin: 0 4px;")
        self.btn_toggle_thumbs.setStyleSheet(f"background: transparent; border: none; color: {text_secondary}; font-size: 12px; font-family: '{font}';")

        # Actualizar miniaturas
        self._render_thumbnails()

    def _get_file_size_label(self) -> str:
        try:
            p = Path(self.file_paths[self.selected_file_index])
            if p.exists():
                sz = p.stat().st_size
                if sz < 1024 * 1024:
                    return f"{sz / 1024:.0f} KB · {self.settings.resolution} PPI"
                return f"{sz / (1024 * 1024):.1f} MB · {self.settings.resolution} PPI"
        except Exception:
            pass
        return f"428 KB · {self.settings.resolution} PPI"

    def _render_thumbnails(self):
        if not hasattr(self, "thumbs_layout"):
            return

        while self.thumbs_layout.count():
            item = self.thumbs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        palette = self.theme_mgr.get_accent_palette()
        is_light = (self.theme_mgr.current_mode == "light")
        text_secondary = "#71717A" if is_light else "#A1A1AA"

        for p_num in range(1, min(6, self.total_pages + 1)):
            thumb_btn = QPushButton()
            thumb_btn.setFixedSize(50, 66)
            thumb_btn.setCursor(Qt.PointingHandCursor)
            is_active = (p_num == self.active_page)

            border_col = palette.primary if is_active else ("#E4E4E7" if is_light else "rgba(255, 255, 255, 0.12)")
            thumb_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #ffffff;
                    border: 2px solid {border_col};
                    border-radius: 4px;
                }}
            """)
            base_img = self._get_page_image(p_num)
            thumb_img = base_img.resize((46, 62), Image.Resampling.BOX)
            thumb_btn.setIcon(pil_to_qpixmap(thumb_img))
            thumb_btn.setIconSize(QSize(46, 62))
            thumb_btn.clicked.connect(lambda _, pn=p_num: self._go_to_page(pn))

            col = QVBoxLayout()
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(2)
            col.addWidget(thumb_btn, 0, Qt.AlignCenter)
            lbl_num = QLabel(str(p_num))
            num_color = palette.text if is_active else text_secondary
            num_weight = "bold" if is_active else "normal"
            lbl_num.setStyleSheet(f"font-size: 11px; font-family: monospace; color: {num_color}; font-weight: {num_weight};")
            col.addWidget(lbl_num, 0, Qt.AlignCenter)

            w = QWidget()
            w.setLayout(col)
            self.thumbs_layout.addWidget(w)

        self.thumbs_layout.addStretch()

    def _update_setting(self, key: str, value):
        setattr(self.settings, key, value)
        self.lbl_fsize.setText(self._get_file_size_label())
        self._update_previews()

    def _on_color_space_changed(self, idx: int):
        self.settings.color_space = self.combo_color.currentData()
        self._update_previews()

    def _on_border_toggled(self, checked: bool):
        self.settings.border = checked
        self._update_previews()

    def _set_paper_size(self, size_name: str):
        self.settings.paper_size = size_name
        self._update_previews()

    def _reset_defaults(self):
        self.settings = ScanSettings()
        self.combo_color.setCurrentIndex(0)
        self.switch_border.setChecked(True)
        self.slider_rotate.set_value(self.settings.rotate)
        self.slider_variance.set_value(self.settings.rotation_variance)
        self.slider_brightness.set_value(self.settings.brightness)
        self.slider_contrast.set_value(self.settings.contrast)
        self.slider_blur.set_value(self.settings.blur)
        self.slider_noise.set_value(self.settings.noise)
        self.slider_yellowing.set_value(self.settings.yellowing)
        self.slider_resolution.set_value(self.settings.resolution)
        self.btn_a4.setChecked(True)
        self._update_previews()

    def _on_file_changed(self, idx: int):
        self.selected_file_index = idx
        self.active_page = 1
        self._load_current_document()
        self.lbl_fsize.setText(self._get_file_size_label())
        self._render_thumbnails()
        self._update_previews()

    def _prev_page(self):
        if self.active_page > 1:
            self._go_to_page(self.active_page - 1)

    def _next_page(self):
        if self.active_page < self.total_pages:
            self._go_to_page(self.active_page + 1)

    def _go_to_page(self, page_num: int):
        self.active_page = page_num
        self.lbl_page_info.setText(f"Página {self.active_page} de {self.total_pages}")
        self.btn_prev_page.setEnabled(self.active_page > 1)
        self.btn_next_page.setEnabled(self.active_page < self.total_pages)
        self._render_thumbnails()
        self._update_previews()

    def _toggle_thumbnails(self):
        self.show_thumbnails = not self.show_thumbnails
        self.thumbs_container.setVisible(self.show_thumbnails)
        self.btn_toggle_thumbs.setText("Ocultar miniaturas" if self.show_thumbnails else "Mostrar miniaturas")

    def _update_previews(self):
        """Actualiza en tiempo real las vistas previas Antes y Después."""
        self.lbl_page_info.setText(f"Página {self.active_page} de {self.total_pages}")
        self.btn_prev_page.setEnabled(self.active_page > 1)
        self.btn_next_page.setEnabled(self.active_page < self.total_pages)

        # 1. Obtener imagen base del documento original
        base_img = self._get_page_image(self.active_page)

        # 2. Renderizar "Antes (PDF plano)"
        w_view, h_view = self.view_before.width(), self.view_before.height()
        aspect = 210.0 / 297.0 if self.settings.paper_size == "a4" else 8.5 / 11.0
        target_w = int(h_view * aspect)
        if target_w > w_view:
            target_w = w_view
            target_h = int(target_w / aspect)
        else:
            target_h = h_view

        scaled_before = base_img.resize((target_w - 10, target_h - 10), Image.Resampling.BILINEAR)
        self.view_before.setPixmap(pil_to_qpixmap(scaled_before))

        # 3. Aplicar efectos de escaneo y renderizar "Después (Vista previa escaneada)"
        scanned_img = apply_scan_effects_to_image(
            scaled_before,
            self.settings,
            page_index=self.active_page,
            preview_scale=float(target_w) / 595.0,
        )
        self.view_after.setPixmap(pil_to_qpixmap(scanned_img))

    def _on_generate_clicked(self):
        """Genera el PDF escaneado aplicando todos los parámetros a todas las páginas."""
        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("Generando PDF escaneado...")

        try:
            for file_path in self.file_paths:
                src = Path(file_path)
                out_pdf = src.parent / f"{src.stem}_escaneado.pdf"
                counter = 1
                while out_pdf.exists():
                    out_pdf = src.parent / f"{src.stem}_escaneado ({counter}).pdf"
                    counter += 1

                self._process_single_scanned_pdf(src, out_pdf)
            self.close()
        except Exception as e:
            print(f"[Scan PDF Generate Error]: {e}", file=sys.stderr)
            self.close()

    def _process_single_scanned_pdf(self, src: Path, out_pdf: Path):
        """Procesa todas las páginas del archivo aplicando los efectos de escaneo a resolución final."""
        temp_input = Path(tempfile.gettempdir()) / f"lime_in_{uuid.uuid4().hex[:8]}.pdf"
        try:
            if not ensure_pdf_from_any(src, temp_input):
                return

            doc_in = fitz.open(str(temp_input))
            doc_out = fitz.open()

            res = max(72, min(300, self.settings.resolution))

            for page_idx in range(len(doc_in)):
                page = doc_in.load_page(page_idx)
                pix = page.get_pixmap(dpi=res, alpha=False)
                pil_page = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                scanned_pil = apply_scan_effects_to_image(
                    pil_page,
                    self.settings,
                    page_index=page_idx + 1,
                    preview_scale=res / 140.0,
                )

                buf = io.BytesIO()
                scanned_pil.save(buf, format="JPEG", quality=90, optimize=True)
                buf.seek(0)

                new_page = doc_out.new_page(width=page.rect.width, height=page.rect.height)
                new_page.insert_image(new_page.rect, stream=buf.getvalue())

            doc_out.save(str(out_pdf), garbage=4, deflate=True)
            doc_out.close()
            doc_in.close()
        finally:
            if temp_input.exists():
                try:
                    temp_input.unlink()
                except Exception:
                    pass

    def _cleanup(self):
        if hasattr(self, "theme_mgr"):
            self.theme_mgr.remove_listener(self._apply_theme)
        if self._pdf_doc:
            try:
                self._pdf_doc.close()
            except Exception:
                pass
            self._pdf_doc = None
        if self._temp_converted_pdf and os.path.exists(self._temp_converted_pdf):
            try:
                os.remove(self._temp_converted_pdf)
            except Exception:
                pass
            self._temp_converted_pdf = None

    def closeEvent(self, event):
        self._cleanup()
        event.accept()
