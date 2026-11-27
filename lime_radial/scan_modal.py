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

    def __init__(self, checked=True, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(38, 21)
        self.setCursor(Qt.PointingHandCursor)

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
        bg = QColor("#14b8a6") if self._checked else QColor("#3f3f46")
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
        self.lbl_title.setStyleSheet("color: #d4d4d8; font-size: 12px; font-weight: normal;")
        self.lbl_value = QLabel()
        self.lbl_value.setStyleSheet("color: #a1a1aa; font-family: monospace; font-size: 11.5px;")
        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(self.lbl_value)
        layout.addLayout(header)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(min_val * self._multiplier), int(max_val * self._multiplier))
        self.slider.setValue(int(value * self._multiplier))
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #36373b;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #14b8a6;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #f8fafc;
                border: 1.5px solid rgba(0, 0, 0, 0.25);
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #ffffff;
                border: 1.5px solid #14b8a6;
            }
        """)
        self.slider.valueChanged.connect(self._on_slider_change)
        layout.addWidget(self.slider)

        self._update_display(value)

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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
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
        self._load_current_document()

        self._build_ui()
        self._update_previews()

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

        card = QFrame(self)
        card.setObjectName("scanCard")
        card.setStyleSheet("""
            QFrame#scanCard {
                background-color: #141416;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 14px;
            }
            QLabel {
                color: #f4f4f5;
                font-family: "%s";
            }
        """ % FONT_FAMILY)
        root.addWidget(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ---------------- 1. Top Header ----------------
        header = QFrame(card)
        header.setFixedHeight(46)
        header.setStyleSheet("background-color: #18181b; border-bottom: 1px solid rgba(255, 255, 255, 0.08);")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 16, 0)
        h_layout.setSpacing(10)

        # Icono de sliders teal
        lbl_icon = QLabel()
        pix_icon = QPixmap(18, 18)
        pix_icon.fill(Qt.transparent)
        p = QPainter(pix_icon)
        draw_icon_path(p, "sliders", 9, 9, 16, QColor("#14b8a6"))
        p.end()
        lbl_icon.setPixmap(pix_icon)
        h_layout.addWidget(lbl_icon)

        # Título
        lbl_title = QLabel("Aplanar PDF — Vista previa de escaneo")
        lbl_title.setStyleSheet("font-size: 13.5px; font-weight: bold; color: #f4f4f5;")
        h_layout.addWidget(lbl_title)

        if len(self.file_paths) > 1:
            lbl_count = QLabel(f"· {len(self.file_paths)} archivos")
            lbl_count.setStyleSheet("font-size: 11.5px; color: #a1a1aa; font-family: monospace;")
            h_layout.addWidget(lbl_count)

        h_layout.addStretch()

        # Botón Restablecer
        self.btn_reset = QPushButton(" Restablecer")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                color: #a1a1aa;
                font-size: 11.5px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.06);
                color: #ffffff;
            }
        """)
        pix_rst = QPixmap(14, 14)
        pix_rst.fill(Qt.transparent)
        p = QPainter(pix_rst)
        draw_icon_path(p, "rotate_ccw", 7, 7, 12, QColor("#a1a1aa"))
        p.end()
        self.btn_reset.setIcon(pix_rst)
        self.btn_reset.clicked.connect(self._reset_defaults)
        h_layout.addWidget(self.btn_reset)

        # Botón Cerrar (×) en la esquina superior derecha
        self.btn_close = QPushButton()
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.09);
            }
        """)
        pix_cls = QPixmap(16, 16)
        pix_cls.fill(Qt.transparent)
        p = QPainter(pix_cls)
        draw_icon_path(p, "close", 8, 8, 12, QColor("#a1a1aa"))
        p.end()
        self.btn_close.setIcon(pix_cls)
        self.btn_close.clicked.connect(self.reject)
        h_layout.addWidget(self.btn_close)

        card_layout.addWidget(header)

        # ---------------- 2. Main Body: Sidebar + Previews ----------------
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # === Sidebar izquierdo de controles (310px) ===
        sidebar = QFrame()
        sidebar.setFixedWidth(310)
        sidebar.setStyleSheet("background-color: #161619; border-right: 1px solid rgba(255, 255, 255, 0.08);")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(10)

        # Card de Información de Archivo
        card_file = QFrame()
        card_file.setStyleSheet("background-color: #1b1b1f; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;")
        cf_layout = QVBoxLayout(card_file)
        cf_layout.setContentsMargins(10, 10, 10, 10)
        cf_layout.setSpacing(4)

        row_f = QHBoxLayout()
        row_f.setSpacing(6)
        lbl_clip = QLabel()
        pix_clip = QPixmap(14, 14)
        pix_clip.fill(Qt.transparent)
        p = QPainter(pix_clip)
        draw_icon_path(p, "paperclip", 7, 7, 12, QColor("#a1a1aa"))
        p.end()
        lbl_clip.setPixmap(pix_clip)
        row_f.addWidget(lbl_clip)

        if len(self.file_paths) > 1:
            self.combo_files = QComboBox()
            self.combo_files.addItems([Path(f).name for f in self.file_paths])
            self.combo_files.setStyleSheet("background: transparent; color: #f4f4f5; font-size: 12px; border: none;")
            self.combo_files.currentIndexChanged.connect(self._on_file_changed)
            row_f.addWidget(self.combo_files)
        else:
            lbl_fname = QLabel(Path(self.file_paths[0]).name)
            lbl_fname.setStyleSheet("color: #e4e4e7; font-size: 12.5px; font-weight: 500;")
            row_f.addWidget(lbl_fname)
        cf_layout.addLayout(row_f)

        self.lbl_fsize = QLabel(self._get_file_size_label())
        self.lbl_fsize.setStyleSheet("color: #a1a1aa; font-family: monospace; font-size: 11px; margin-left: 20px;")
        cf_layout.addWidget(self.lbl_fsize)
        side_layout.addWidget(card_file)

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
        card_scan = QFrame()
        card_scan.setStyleSheet("background-color: #1b1b1f; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;")
        cs_layout = QVBoxLayout(card_scan)
        cs_layout.setContentsMargins(12, 10, 12, 12)
        cs_layout.setSpacing(10)

        lbl_scan_sec = QLabel("⚙️  Configuración de escaneo")
        lbl_scan_sec.setStyleSheet("font-size: 12.5px; font-weight: bold; color: #f4f4f5; margin-bottom: 2px;")
        cs_layout.addWidget(lbl_scan_sec)

        # Fila: Espacio de color + Borde
        row_cb = QHBoxLayout()
        row_cb.setSpacing(10)

        v_col = QVBoxLayout()
        v_col.setSpacing(4)
        lbl_c_title = QLabel("Espacio de color")
        lbl_c_title.setStyleSheet("font-size: 11.5px; color: #d4d4d8;")
        self.combo_color = QComboBox()
        self.combo_color.addItem("Color", "color")
        self.combo_color.addItem("Escala de Grises", "grayscale")
        self.combo_color.addItem("Blanco y Negro", "bw")
        self.combo_color.setStyleSheet("""
            QComboBox {
                background-color: #121215;
                color: #f4f4f5;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QComboBox:focus {
                border: 1px solid #14b8a6;
            }
        """)
        self.combo_color.currentIndexChanged.connect(self._on_color_space_changed)
        v_col.addWidget(lbl_c_title)
        v_col.addWidget(self.combo_color)
        row_cb.addLayout(v_col)

        v_bor = QVBoxLayout()
        v_bor.setSpacing(4)
        lbl_b_title = QLabel("Borde")
        lbl_b_title.setStyleSheet("font-size: 11.5px; color: #d4d4d8;")
        self.switch_border = ToggleSwitch(checked=True)
        self.switch_border.toggled.connect(self._on_border_toggled)
        v_bor.addWidget(lbl_b_title)
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

        sw_layout.addWidget(card_scan)

        # Acordeón: Configuración de Papel
        card_paper = QFrame()
        card_paper.setStyleSheet("background-color: #1b1b1f; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;")
        cp_layout = QVBoxLayout(card_paper)
        cp_layout.setContentsMargins(12, 10, 12, 10)
        cp_layout.setSpacing(8)

        lbl_paper_sec = QLabel("📄  Configuración de papel")
        lbl_paper_sec.setStyleSheet("font-size: 12.5px; font-weight: bold; color: #f4f4f5;")
        cp_layout.addWidget(lbl_paper_sec)

        lbl_psize = QLabel("Tamaño de hoja")
        lbl_psize.setStyleSheet("font-size: 11.5px; color: #a1a1aa;")
        cp_layout.addWidget(lbl_psize)

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

        style_pbtn = """
            QPushButton {
                background-color: #121215;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 5px;
                padding: 5px 0;
                color: #a1a1aa;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: rgba(20, 184, 166, 0.15);
                border: 1px solid #14b8a6;
                color: #ffffff;
            }
        """
        self.btn_a4.setStyleSheet(style_pbtn)
        self.btn_letter.setStyleSheet(style_pbtn)
        self.btn_a4.clicked.connect(lambda: self._set_paper_size("a4"))
        self.btn_letter.clicked.connect(lambda: self._set_paper_size("letter"))
        row_pbtns.addWidget(self.btn_a4)
        row_pbtns.addWidget(self.btn_letter)
        cp_layout.addLayout(row_pbtns)

        sw_layout.addWidget(card_paper)
        sw_layout.addStretch()

        scroll.setWidget(scroll_widget)
        side_layout.addWidget(scroll, 1)

        # Botón inferior: Generar PDF escaneado
        self.btn_generate = QPushButton("  Generar PDF escaneado")
        self.btn_generate.setFixedHeight(40)
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.setStyleSheet("""
            QPushButton {
                background-color: rgba(20, 184, 166, 0.12);
                border: 1px solid #14b8a6;
                border-radius: 8px;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(20, 184, 166, 0.22);
            }
            QPushButton:pressed {
                background-color: #14b8a6;
            }
        """)
        pix_gen = QPixmap(16, 16)
        pix_gen.fill(Qt.transparent)
        p = QPainter(pix_gen)
        draw_icon_path(p, "file_check", 8, 8, 14, QColor("#2dd4bf"))
        p.end()
        self.btn_generate.setIcon(pix_gen)
        self.btn_generate.clicked.connect(self._on_generate_clicked)
        side_layout.addWidget(self.btn_generate)

        body.addWidget(sidebar)

        # === Right Preview Area (Comparativa Antes y Después) ===
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #101012;")
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.setSpacing(0)

        # Canvas central con los dos documentos
        center_canvas = QFrame()
        center_canvas.setStyleSheet("background-color: #101012;")
        canvas_layout = QHBoxLayout(center_canvas)
        canvas_layout.setContentsMargins(30, 20, 30, 20)
        canvas_layout.setSpacing(30)
        canvas_layout.setAlignment(Qt.AlignCenter)

        # Columna 1: Antes (PDF plano)
        col_before = QVBoxLayout()
        col_before.setSpacing(8)
        col_before.setAlignment(Qt.AlignCenter)
        lbl_b_title = QLabel("Antes (PDF plano)")
        lbl_b_title.setStyleSheet("font-size: 11.5px; font-weight: 500; color: #9ca3af;")
        col_before.addWidget(lbl_b_title, 0, Qt.AlignCenter)

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
        lbl_a_title = QLabel("Después (Vista previa escaneada)")
        lbl_a_title.setStyleSheet("font-size: 11.5px; font-weight: bold; color: #2dd4bf;")
        col_after.addWidget(lbl_a_title, 0, Qt.AlignCenter)

        self.view_after = QLabel()
        self.view_after.setFixedSize(330, 460)
        self.view_after.setAlignment(Qt.AlignCenter)
        self.view_after.setStyleSheet("""
            background-color: #e5e5e3;
            border-radius: 2px;
        """)
        col_after.addWidget(self.view_after, 0, Qt.AlignCenter)
        canvas_layout.addLayout(col_after)

        rp_layout.addWidget(center_canvas, 1)

        # Barra inferior de Paginación y Miniaturas
        bottom_strip = QFrame()
        bottom_strip.setStyleSheet("background-color: #18181b; border-top: 1px solid rgba(255, 255, 255, 0.08);")
        bs_layout = QVBoxLayout(bottom_strip)
        bs_layout.setContentsMargins(16, 8, 16, 8)
        bs_layout.setSpacing(6)

        # Fila de control de página
        row_page = QHBoxLayout()
        self.lbl_page_info = QLabel("Página 1 de 2")
        self.lbl_page_info.setStyleSheet("font-size: 12px; color: #a1a1aa; font-family: monospace;")
        row_page.addWidget(self.lbl_page_info)
        row_page.addStretch()

        self.btn_prev_page = QPushButton()
        self.btn_prev_page.setFixedSize(28, 28)
        self.btn_prev_page.setCursor(Qt.PointingHandCursor)
        self.btn_prev_page.setStyleSheet("background-color: #222226; border: 1px solid rgba(255,255,255,0.08); border-radius: 5px;")
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
        self.btn_next_page.setStyleSheet("background-color: #222226; border: 1px solid rgba(255,255,255,0.08); border-radius: 5px;")
        pix_pr = QPixmap(14, 14)
        pix_pr.fill(Qt.transparent)
        p = QPainter(pix_pr)
        draw_icon_path(p, "chevron_right", 7, 7, 12, QColor("#a1a1aa"))
        p.end()
        self.btn_next_page.setIcon(pix_pr)
        self.btn_next_page.clicked.connect(self._next_page)
        row_page.addWidget(self.btn_next_page)

        lbl_sep = QLabel("|")
        lbl_sep.setStyleSheet("color: rgba(255,255,255,0.1); margin: 0 4px;")
        row_page.addWidget(lbl_sep)

        self.btn_toggle_thumbs = QPushButton("Ocultar miniaturas")
        self.btn_toggle_thumbs.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_thumbs.setStyleSheet("background: transparent; border: none; color: #a1a1aa; font-size: 12px;")
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

        self._render_thumbnails()

        rp_layout.addWidget(bottom_strip)
        body.addWidget(right_panel, 1)

        card_layout.addLayout(body, 1)

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
        # Limpiar miniaturas existentes
        while self.thumbs_layout.count():
            item = self.thumbs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for p_num in range(1, min(6, self.total_pages + 1)):
            thumb_btn = QPushButton()
            thumb_btn.setFixedSize(50, 66)
            thumb_btn.setCursor(Qt.PointingHandCursor)
            is_active = (p_num == self.active_page)

            border_col = "#14b8a6" if is_active else "transparent"
            thumb_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #ffffff;
                    border: 2px solid {border_col};
                    border-radius: 3px;
                }}
            """)
            # Renderizar miniatura
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
            lbl_num.setStyleSheet(f"font-size: 11px; font-family: monospace; color: {'#2dd4bf' if is_active else '#71717a'};")
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
            self.accept()
        except Exception as e:
            print(f"[Scan PDF Generate Error]: {e}", file=sys.stderr)
            self.accept()

    def _process_single_scanned_pdf(self, src: Path, out_pdf: Path):
        """Procesa todas las páginas del archivo aplicando los efectos de escaneo a resolución final."""
        # Asegurar PDF inicial
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

                # Aplicar efectos completos de escaneado
                scanned_pil = apply_scan_effects_to_image(
                    pil_page,
                    self.settings,
                    page_index=page_idx + 1,
                    preview_scale=res / 140.0,
                )

                # Guardar página en documento final
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

    def accept(self):
        self._cleanup()
        super().accept()

    def reject(self):
        self._cleanup()
        super().reject()

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)
        super().closeEvent(event)
