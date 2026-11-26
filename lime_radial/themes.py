"""
Sistema de temas para Lime Radial Windows.
Soporta familias: 'classic', 'lime', 'tangerine', 'acrylic'
y modos de apariencia: 'light' y 'dark'.
Persiste la selección del usuario mediante QSettings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QLinearGradient, QRadialGradient


@dataclass
class RadialThemeSpec:
    id: str
    family: str  # 'classic' | 'lime' | 'tangerine' | 'acrylic'
    mode: str    # 'light' | 'dark'
    name: str
    subtitle: str
    swatch: str
    backdrop_fill: str
    backdrop_stroke: str
    backdrop_stroke_width: float
    pith_ring_stroke: Optional[str]
    wedge_fill: str
    wedge_stroke: str
    wedge_stroke_width: float
    wedge_active_fill_type: str  # 'solid' | 'gradient'
    wedge_active_colors: Tuple[str, ...]
    wedge_active_stroke: str
    wedge_text: str
    wedge_active_text: str
    wedge_icon: str
    wedge_active_icon: str
    center_fill: str
    center_stroke: str
    center_text: str
    active_scale: float = 1.03
    show_pulp_veins: bool = True
    wedge_corner_out: float = 14.0
    wedge_corner_in: float = 11.0
    half_gap: float = 2.9


CLASSIC_THEME = RadialThemeSpec(
    id="classic",
    family="classic",
    mode="dark",
    name="Clásico",
    subtitle="Diseño base con contraste naranja",
    swatch="#FF5000",
    backdrop_fill="rgba(12, 12, 12, 0.56)",
    backdrop_stroke="rgba(210, 198, 180, 0.36)",
    backdrop_stroke_width=1.75,
    pith_ring_stroke=None,
    wedge_fill="#EBEBEB",
    wedge_stroke="rgba(255, 255, 255, 0.4)",
    wedge_stroke_width=0.65,
    wedge_active_fill_type="solid",
    wedge_active_colors=("#FF5000", "#E04500"),
    wedge_active_stroke="rgba(255, 190, 150, 0.65)",
    wedge_text="#262626",
    wedge_active_text="#FFFFFF",
    wedge_icon="#323232",
    wedge_active_icon="#FFFFFF",
    center_fill="#EFEFEF",
    center_stroke="rgba(255, 255, 255, 0.65)",
    center_text="#222222",
    active_scale=1.0,
    show_pulp_veins=False,
    wedge_corner_out=11.5,
    wedge_corner_in=9.5,
    half_gap=2.6,
)

LIGHT_THEMES: Dict[str, RadialThemeSpec] = {
    "lime": RadialThemeSpec(
        id="lime-light",
        family="lime",
        mode="light",
        name="Lima Escarchada",
        subtitle="Gajos verde lima claros con halo de cáscara",
        swatch="#78C81E",
        backdrop_fill="rgba(232, 245, 224, 0.78)",
        backdrop_stroke="rgba(132, 204, 22, 0.72)",
        backdrop_stroke_width=2.2,
        pith_ring_stroke="rgba(101, 163, 13, 0.35)",
        wedge_fill="rgba(255, 255, 255, 0.94)",
        wedge_stroke="rgba(163, 230, 53, 0.55)",
        wedge_stroke_width=0.85,
        wedge_active_fill_type="gradient",
        wedge_active_colors=("#A3E635", "#65A30D"),
        wedge_active_stroke="rgba(236, 252, 203, 0.95)",
        wedge_text="#1A2E1A",
        wedge_active_text="#0F1A0B",
        wedge_icon="#254225",
        wedge_active_icon="#0F1A0B",
        center_fill="#FFFFFF",
        center_stroke="rgba(132, 204, 22, 0.75)",
        center_text="#192914",
        active_scale=1.03,
        show_pulp_veins=True,
        wedge_corner_out=14.0,
        wedge_corner_in=11.0,
        half_gap=3.1,
    ),
    "tangerine": RadialThemeSpec(
        id="tangerine-light",
        family="tangerine",
        mode="light",
        name="Naranja Jugosa",
        subtitle="Pulpa cálida clara y gajo mandarina vibrante",
        swatch="#F97316",
        backdrop_fill="rgba(255, 244, 232, 0.80)",
        backdrop_stroke="rgba(249, 115, 22, 0.72)",
        backdrop_stroke_width=2.4,
        pith_ring_stroke="rgba(234, 88, 12, 0.3)",
        wedge_fill="rgba(255, 252, 248, 0.95)",
        wedge_stroke="rgba(253, 186, 116, 0.5)",
        wedge_stroke_width=0.85,
        wedge_active_fill_type="gradient",
        wedge_active_colors=("#FB923C", "#F97316", "#EA580C"),
        wedge_active_stroke="rgba(255, 237, 213, 0.95)",
        wedge_text="#3A1D0C",
        wedge_active_text="#FFFFFF",
        wedge_icon="#4A2511",
        wedge_active_icon="#FFFFFF",
        center_fill="#FFFFFF",
        center_stroke="rgba(249, 115, 22, 0.7)",
        center_text="#2A1408",
        active_scale=1.032,
        show_pulp_veins=True,
        wedge_corner_out=15.0,
        wedge_corner_in=12.0,
        half_gap=2.9,
    ),
    "acrylic": RadialThemeSpec(
        id="acrylic-light",
        family="acrylic",
        mode="light",
        name="Pulpa Acrílica",
        subtitle="Cristal claro con borde del color del gajo activo",
        swatch="#FF5D47",
        backdrop_fill="rgba(246, 248, 252, 0.72)",
        backdrop_stroke="#FF5D47",
        backdrop_stroke_width=2.4,
        pith_ring_stroke="rgba(255, 93, 71, 0.28)",
        wedge_fill="rgba(255, 255, 255, 0.85)",
        wedge_stroke="rgba(255, 255, 255, 0.95)",
        wedge_stroke_width=0.9,
        wedge_active_fill_type="gradient",
        wedge_active_colors=("#FF7A45", "#F43F5E"),
        wedge_active_stroke="rgba(255, 228, 220, 0.95)",
        wedge_text="#1F2328",
        wedge_active_text="#FFFFFF",
        wedge_icon="#2D333B",
        wedge_active_icon="#FFFFFF",
        center_fill="rgba(255, 255, 255, 0.95)",
        center_stroke="#FF5D47",
        center_text="#18181B",
        active_scale=1.035,
        show_pulp_veins=True,
        wedge_corner_out=16.0,
        wedge_corner_in=13.0,
        half_gap=3.4,
    ),
}

DARK_THEMES: Dict[str, RadialThemeSpec] = {
    "lime": RadialThemeSpec(
        id="lime-dark",
        family="lime",
        mode="dark",
        name="Gajos Nocturnos",
        subtitle="Grafito oscuro con contraste ácido de lima",
        swatch="#A3E635",
        backdrop_fill="rgba(10, 11, 13, 0.82)",
        backdrop_stroke="rgba(163, 230, 53, 0.55)",
        backdrop_stroke_width=2.0,
        pith_ring_stroke="rgba(163, 230, 53, 0.22)",
        wedge_fill="rgba(38, 41, 46, 0.94)",
        wedge_stroke="rgba(255, 255, 255, 0.15)",
        wedge_stroke_width=0.9,
        wedge_active_fill_type="gradient",
        wedge_active_colors=("#BEF264", "#84CC16"),
        wedge_active_stroke="rgba(217, 249, 157, 0.85)",
        wedge_text="#E8ECEF",
        wedge_active_text="#0E140B",
        wedge_icon="#D1D5DB",
        wedge_active_icon="#0E140B",
        center_fill="#1B1D20",
        center_stroke="rgba(163, 230, 53, 0.65)",
        center_text="#F3F4F6",
        active_scale=1.028,
        show_pulp_veins=True,
        wedge_corner_out=12.0,
        wedge_corner_in=9.5,
        half_gap=2.7,
    ),
    "tangerine": RadialThemeSpec(
        id="tangerine-dark",
        family="tangerine",
        mode="dark",
        name="Naranja Jugosa",
        subtitle="Modo oscuro tostado con gajo mandarina luminoso",
        swatch="#FB923C",
        backdrop_fill="rgba(20, 12, 8, 0.84)",
        backdrop_stroke="rgba(249, 115, 22, 0.68)",
        backdrop_stroke_width=2.2,
        pith_ring_stroke="rgba(251, 146, 60, 0.25)",
        wedge_fill="rgba(46, 31, 23, 0.94)",
        wedge_stroke="rgba(251, 146, 60, 0.22)",
        wedge_stroke_width=0.85,
        wedge_active_fill_type="gradient",
        wedge_active_colors=("#FB923C", "#F97316", "#EA580C"),
        wedge_active_stroke="rgba(255, 237, 213, 0.88)",
        wedge_text="#FFF1E6",
        wedge_active_text="#FFFFFF",
        wedge_icon="#FDBA74",
        wedge_active_icon="#FFFFFF",
        center_fill="#241710",
        center_stroke="rgba(249, 115, 22, 0.72)",
        center_text="#FFF7ED",
        active_scale=1.032,
        show_pulp_veins=True,
        wedge_corner_out=15.0,
        wedge_corner_in=12.0,
        half_gap=2.9,
    ),
    "acrylic": RadialThemeSpec(
        id="acrylic-dark",
        family="acrylic",
        mode="dark",
        name="Pulpa Acrílica",
        subtitle="Acrílico oscuro con borde del color del gajo activo",
        swatch="#FF5D47",
        backdrop_fill="rgba(16, 18, 22, 0.74)",
        backdrop_stroke="#FF5D47",
        backdrop_stroke_width=2.4,
        pith_ring_stroke="rgba(255, 93, 71, 0.25)",
        wedge_fill="rgba(42, 46, 54, 0.82)",
        wedge_stroke="rgba(255, 255, 255, 0.16)",
        wedge_stroke_width=0.9,
        wedge_active_fill_type="gradient",
        wedge_active_colors=("#FF7A45", "#F43F5E"),
        wedge_active_stroke="rgba(255, 224, 214, 0.9)",
        wedge_text="#F1F5F9",
        wedge_active_text="#FFFFFF",
        wedge_icon="#CBD5E1",
        wedge_active_icon="#FFFFFF",
        center_fill="rgba(28, 31, 37, 0.94)",
        center_stroke="#FF5D47",
        center_text="#F8FAFC",
        active_scale=1.035,
        show_pulp_veins=True,
        wedge_corner_out=16.0,
        wedge_corner_in=13.0,
        half_gap=3.4,
    ),
}


class ThemeManager:
    _instance: Optional[ThemeManager] = None

    def __init__(self):
        self.settings = QSettings("LimeRadial", "LimeRadial")
        self.current_family = self.settings.value("theme_family", "lime")
        self.current_mode = self.settings.value("theme_mode", "dark")
        self._listeners: List[callable] = []

    @classmethod
    def get_instance(cls) -> ThemeManager:
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    def get_theme(self) -> RadialThemeSpec:
        if self.current_family == "classic":
            return CLASSIC_THEME
        mode_map = LIGHT_THEMES if self.current_mode == "light" else DARK_THEMES
        return mode_map.get(self.current_family, DARK_THEMES["lime"])

    def set_mode(self, mode: str):
        if mode in ("light", "dark"):
            self.current_mode = mode
            self.settings.setValue("theme_mode", mode)
            self._notify()

    def set_family(self, family: str):
        if family in ("classic", "lime", "tangerine", "acrylic"):
            self.current_family = family
            self.settings.setValue("theme_family", family)
            self._notify()

    def add_listener(self, callback: callable):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def _notify(self):
        theme = self.get_theme()
        for cb in self._listeners:
            try:
                cb(theme)
            except Exception:
                pass


def parse_qcolor(color_str: str) -> QColor:
    """Convierte cadenas css como 'rgba(10, 11, 13, 0.82)' o '#A3E635' a QColor."""
    c = color_str.strip()
    if c.startswith("#"):
        return QColor(c)
    if c.startswith("rgba"):
        inside = c[c.find("(") + 1 : c.find(")")]
        parts = [p.strip() for p in inside.split(",")]
        if len(parts) == 4:
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            a = int(float(parts[3]) * 255)
            return QColor(r, g, b, a)
    if c.startswith("rgb"):
        inside = c[c.find("(") + 1 : c.find(")")]
        parts = [p.strip() for p in inside.split(",")]
        if len(parts) == 3:
            return QColor(int(parts[0]), int(parts[1]), int(parts[2]))
    return QColor(c)
