"""
Sistema de iconos vectoriales minimalistas y fuentes para Lime Radial Windows.
Dibuja iconos vectoriales con QPainterPath en alta resolución.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontDatabase,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

FONT_FAMILY = "Segoe UI"


def load_custom_fonts():
    """Carga Plus Jakarta Sans si está disponible en la carpeta fonts."""
    global FONT_FAMILY
    candidates = [
        Path(__file__).parent / "fonts" / "PlusJakartaSans.ttf",
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.insert(0, Path(sys._MEIPASS) / "lime_radial" / "fonts" / "PlusJakartaSans.ttf")
        candidates.insert(1, Path(sys._MEIPASS) / "fonts" / "PlusJakartaSans.ttf")

    for font_path in candidates:
        if font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    FONT_FAMILY = families[0]
                    return FONT_FAMILY
    return "Segoe UI"


def draw_minimal_icon(painter: QPainter, icon_name: str, center: QPointF, size: float = 18.0, color: QColor = QColor(255, 255, 255)):
    """Dibuja un icono vectorial minimalista con trazos nítidos."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    
    pen = QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    
    cx, cy = center.x(), center.y()
    hs = size / 2.0
    
    name = icon_name.upper().strip()
    
    if name == "COMPRESS":
        # Flechas convergiendo hacia el centro
        d = hs * 0.75
        # Flecha superior izquierda hacia centro
        p = QPainterPath()
        p.moveTo(cx - d, cy - d)
        p.lineTo(cx - 2, cy - 2)
        p.moveTo(cx - d + 3, cy - 2)
        p.lineTo(cx - 2, cy - 2)
        p.lineTo(cx - 2, cy - d + 3)
        # Flecha inferior derecha hacia centro
        p.moveTo(cx + d, cy + d)
        p.lineTo(cx + 2, cy + 2)
        p.moveTo(cx + d - 3, cy + 2)
        p.lineTo(cx + 2, cy + 2)
        p.lineTo(cx + 2, cy + d - 3)
        painter.drawPath(p)

    elif name == "CROP":
        # Marcadores de recorte entrelazados
        d = hs * 0.75
        p = QPainterPath()
        p.moveTo(cx - d, cy - d + 4)
        p.lineTo(cx + d - 4, cy - d + 4)
        p.lineTo(cx + d - 4, cy + d)
        
        p.moveTo(cx + d, cy + d - 4)
        p.lineTo(cx - d + 4, cy + d - 4)
        p.lineTo(cx - d + 4, cy - d)
        painter.drawPath(p)

    elif name in ("SPLIT PDF", "SPLIT", "DIVIDIR", "DIVIDIR PDF"):
        # Dos páginas separándose limpiamente
        w, h = hs * 0.42, hs * 0.85
        p = QPainterPath()
        # Página izquierda
        p.addRoundedRect(QRectF(cx - w * 2 - 1.5, cy - h, w * 2, h * 2), 1.5, 1.5)
        # Página derecha
        p.addRoundedRect(QRectF(cx + 1.5, cy - h, w * 2, h * 2), 1.5, 1.5)
        painter.drawPath(p)

    elif name in ("FLATTEN PDF", "FLATTEN", "APLANAR", "APLANAR PDF"):
        # Capas comprimidas en una sola hoja plana
        d = hs * 0.78
        p = QPainterPath()
        # Capa superior
        p.moveTo(cx - d + 2, cy - d + 2)
        p.lineTo(cx + d - 2, cy - d + 2)
        # Flecha hacia abajo (aplanar)
        p.moveTo(cx, cy - d + 4)
        p.lineTo(cx, cy + 2)
        p.moveTo(cx - 3, cy - 1)
        p.lineTo(cx, cy + 2)
        p.lineTo(cx + 3, cy - 1)
        # Base sólida plana inferior
        p.addRoundedRect(QRectF(cx - d, cy + 3.5, d * 2, hs * 0.45), 1.5, 1.5)
        painter.drawPath(p)

    elif name in ("CREATE PDF", "CREAR PDF", "PDF"):
        # Documento con esquina doblada o signo más
        w, h = hs * 0.7, hs * 0.9
        p = QPainterPath()
        p.addRoundedRect(QRectF(cx - w, cy - h, w * 2, h * 2), 2, 2)
        # Signo más en el centro
        p.moveTo(cx - 3, cy)
        p.lineTo(cx + 3, cy)
        p.moveTo(cx, cy - 3)
        p.lineTo(cx, cy + 3)
        painter.drawPath(p)

    elif name in ("COLLAGE",):
        # Cuadrícula 2x2 o split
        d = hs * 0.8
        p = QPainterPath()
        p.addRoundedRect(QRectF(cx - d, cy - d, d * 0.9, d * 1.9), 1.5, 1.5)
        p.addRoundedRect(QRectF(cx + 1, cy - d, d * 0.9, d * 0.9), 1.5, 1.5)
        p.addRoundedRect(QRectF(cx + 1, cy + 1, d * 0.9, d * 0.9), 1.5, 1.5)
        painter.drawPath(p)

    elif name in ("METADATA", "METADATOS"):
        # Etiqueta / Tag con orificio
        d = hs * 0.8
        p = QPainterPath()
        p.moveTo(cx - d + 3, cy - d)
        p.lineTo(cx + d - 4, cy - d)
        p.lineTo(cx + d, cy)
        p.lineTo(cx, cy + d)
        p.lineTo(cx - d, cy + 2)
        p.closeSubpath()
        painter.drawPath(p)
        painter.drawEllipse(QPointF(cx - d + 4, cy - d + 4), 1.2, 1.2)

    elif name in ("EDIT", "EDITAR"):
        # Sliders de ajuste horizontales
        d = hs * 0.75
        p = QPainterPath()
        # Línea 1
        p.moveTo(cx - d, cy - 4)
        p.lineTo(cx + d, cy - 4)
        # Línea 2
        p.moveTo(cx - d, cy + 4)
        p.lineTo(cx + d, cy + 4)
        painter.drawPath(p)
        # Perillas
        painter.drawEllipse(QPointF(cx - 2, cy - 4), 2, 2)
        painter.drawEllipse(QPointF(cx + 3, cy + 4), 2, 2)

    elif name in ("ANNOTATE", "ANOTAR"):
        # Círculo con lápiz o pluma
        p = QPainterPath()
        p.addEllipse(QPointF(cx, cy), hs * 0.7, hs * 0.7)
        p.moveTo(cx - 3, cy + 3)
        p.lineTo(cx + 4, cy - 4)
        painter.drawPath(p)

    elif name in ("ADD BG", "ADDBG", "AÑADIR FONDO", "FONDO"):
        # Cuadro de imagen paisaje
        d = hs * 0.8
        p = QPainterPath()
        p.addRoundedRect(QRectF(cx - d, cy - d + 2, d * 2, d * 1.6), 2, 2)
        # Montañas
        p.moveTo(cx - d + 2, cy + d - 2)
        p.lineTo(cx - 2, cy - 1)
        p.lineTo(cx + 2, cy + 2)
        p.lineTo(cx + d - 2, cy - 2)
        painter.drawPath(p)

    elif name in ("REDACT", "CENSURAR"):
        # Ojo con barra diagonal
        d = hs * 0.8
        p = QPainterPath()
        p.moveTo(cx - d, cy)
        p.quadTo(cx, cy - d * 0.7, cx + d, cy)
        p.quadTo(cx, cy + d * 0.7, cx - d, cy)
        # Barra diagonal
        p.moveTo(cx - d + 2, cy + d - 2)
        p.lineTo(cx + d - 2, cy - d + 2)
        painter.drawPath(p)

    elif name in ("COMPRESS", "COMPRIMIR"):
        # Flechas de compresión enfrentadas
        d = hs * 0.75
        p = QPainterPath()
        # Flecha superior
        p.moveTo(cx, cy - d)
        p.lineTo(cx, cy - 2)
        p.moveTo(cx - 3, cy - 5)
        p.lineTo(cx, cy - 2)
        p.lineTo(cx + 3, cy - 5)
        # Flecha inferior
        p.moveTo(cx, cy + d)
        p.lineTo(cx, cy + 2)
        p.moveTo(cx - 3, cy + 5)
        p.lineTo(cx, cy + 2)
        p.lineTo(cx + 3, cy + 5)
        painter.drawPath(p)

    elif name in ("CROP", "RECORTAR"):
        # Marco de encuadre / recorte cruzado
        d = hs * 0.7
        p = QPainterPath()
        # Esquina superior izquierda
        p.moveTo(cx - d - 2, cy - d + 3)
        p.lineTo(cx - d + 3, cy - d + 3)
        p.lineTo(cx - d + 3, cy - d - 2)
        # Esquina inferior derecha
        p.moveTo(cx + d + 2, cy + d - 3)
        p.lineTo(cx + d - 3, cy + d - 3)
        p.lineTo(cx + d - 3, cy + d + 2)
        # Rectángulo central punteado o marco
        p.addRect(QRectF(cx - d + 3, cy - d + 3, d * 2 - 6, d * 2 - 6))
        painter.drawPath(p)

    painter.restore()


def draw_lime_fruit_icon(painter: QPainter, target_rect: QRectF):
    """
    Dibuja el icono de la Lima cítrica de alta fidelidad basado en LimeFruitIcon.tsx:
    Cuerpo cítrico dorado/amarillo con degradado, brillo blanco, curvas de pulpa y hoja verde fresca.
    """
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    
    # Escalar para encajar en target_rect (base 64x64)
    scale = min(target_rect.width() / 64.0, target_rect.height() / 64.0)
    cx = target_rect.center().x()
    cy = target_rect.center().y()
    
    painter.translate(cx, cy)
    painter.scale(scale, scale)
    painter.translate(-32, -32)

    # 1. Cuerpo cítrico con degradado radial cálido
    body_grad = QRadialGradient(QPointF(24, 20), 40)
    body_grad.setColorAt(0.0, QColor("#FFF08A"))
    body_grad.setColorAt(0.55, QColor("#FCD34D"))
    body_grad.setColorAt(1.0, QColor("#E59E1B"))

    painter.save()
    painter.translate(33, 34)
    painter.rotate(-32)

    body_path = QPainterPath()
    body_path.moveTo(0, -20)
    body_path.cubicTo(4, -18.5, 14, -12, 14, 0)
    body_path.cubicTo(14, 12, 4, 18.5, 0, 20)
    body_path.cubicTo(-4, 18.5, -14, 12, -14, 0)
    body_path.cubicTo(-14, -12, -4, -18.5, 0, -20)
    body_path.closeSubpath()

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(body_grad))
    painter.drawPath(body_path)

    # Brillo elíptico
    painter.save()
    painter.rotate(-10)
    painter.setBrush(QColor(255, 255, 255, 85))
    painter.drawEllipse(QRectF(-7.7, -13, 6.4, 15))
    painter.restore()

    # Línea sutil de textura de cáscara
    curve_pen = QPen(QColor(180, 95, 10, 80), 1.2, Qt.SolidLine, Qt.RoundCap)
    painter.setPen(curve_pen)
    painter.setBrush(Qt.NoBrush)
    curve_path = QPainterPath()
    curve_path.moveTo(10.5, 8.5)
    curve_path.cubicTo(7.5, 14.5, 2.8, 18.2, 0, 19.6)
    curve_path.cubicTo(-0.6, 19.3, -1.8, 18.6, -3.8, 17.1)
    painter.drawPath(curve_path)

    painter.restore()

    # 2. Hoja verde fresca superior
    leaf_grad = QLinearGradient(0, 0, 32, 32)
    leaf_grad.setColorAt(0.0, QColor("#A3E635"))
    leaf_grad.setColorAt(1.0, QColor("#4D7C0F"))

    leaf_path = QPainterPath()
    leaf_path.moveTo(24, 18)
    leaf_path.cubicTo(19, 11, 11, 11, 9, 14.5)
    leaf_path.cubicTo(12, 18.5, 18.5, 20, 24, 18)
    leaf_path.closeSubpath()

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(leaf_grad))
    painter.drawPath(leaf_path)

    # Nervadura de la hoja
    leaf_vein_pen = QPen(QColor(255, 255, 255, 95), 0.9, Qt.SolidLine, Qt.RoundCap)
    painter.setPen(leaf_vein_pen)
    painter.drawLine(QPointF(11.5, 14.6), QPointF(23.2, 17.8))

    painter.restore()

