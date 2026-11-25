"""
Script de compilación para generar el ejecutable autónomo optimizado LimeRadial.exe
utilizando PyInstaller, purgando módulos innecesarios para reducir el peso.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Configurar codificación segura UTF-8 para evitar errores charmap en Windows CI
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def post_clean_dist(dist_dir: Path):
    """Elimina residuos pesados innecesarios que PyInstaller no purga por defecto."""
    patterns_to_exclude = [
        "onnxruntime", "pymupdf_layout", "layout_", "table_grid",
        "qt6quick", "qt6qml", "opengl32sw",
        "libscipy_openblas", "tkinter", "tcl", "qt6webengine",
        "qt6network"
    ]
    freed = 0
    removed_count = 0
    for f in list(dist_dir.rglob("*")):
        if f.is_file():
            name_lower = f.name.lower()
            if any(p in name_lower for p in patterns_to_exclude):
                freed += f.stat().st_size
                removed_count += 1
                try:
                    f.unlink()
                except Exception:
                    pass

    # Limpiar directorios vacios
    for d in sorted(dist_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if d.is_dir():
            try:
                if not any(d.iterdir()):
                    d.rmdir()
            except Exception:
                pass

    print(f"[LimeRadial] Purgados {removed_count} archivos ({freed / (1024*1024):.2f} MB) innecesarios con exito.")


def build():
    root = Path(__file__).resolve().parent
    print("[LimeRadial] Iniciando empaquetado optimizado de Lime Radial Windows...")

    # Asegurar que el icono existe
    ico_path = root / "lime.ico"
    if not ico_path.exists():
        from PySide6.QtWidgets import QApplication
        from lime_radial.tray import create_lime_icon
        from PIL import Image
        app = QApplication.instance() or QApplication(sys.argv)
        icon = create_lime_icon()
        pix = icon.pixmap(256, 256)
        pix.save(str(root / "lime.png"))
        im = Image.open(str(root / "lime.png"))
        im.save(str(ico_path), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print("[LimeRadial] Icono lime.ico generado exitosamente.")

    # Localizar ffmpeg de imageio_ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_bin = Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        ffmpeg_bin = None

    datas = [
        f"{root / 'lime_radial' / 'fonts'};lime_radial/fonts",
        f"{ico_path};.",
    ]

    binaries = []
    if ffmpeg_bin and ffmpeg_bin.exists():
        binaries.append(f"{ffmpeg_bin};imageio_ffmpeg/binaries")
        print(f"[LimeRadial] FFmpeg binario incluido: {ffmpeg_bin.name}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name=LimeRadial",
        "--windowed",  # Sin ventana de consola negra
        f"--icon={ico_path}",
    ]

    for d in datas:
        cmd.extend(["--add-data", d])

    for b in binaries:
        cmd.extend(["--add-binary", b])

    # Hidden imports esenciales
    hidden_imports = [
        "PIL",
        "PIL.Image",
        "PIL.ImageOps",
        "PIL.ImageEnhance",
        "PIL.ImageFilter",
        "pymupdf",
        "fitz",
        "docx",
        "openpyxl",
        "pptx",
        "win32com",
        "win32com.client",
        "imageio_ffmpeg",
        "pillow_heif",
        "markdown2",
    ]
    for h in hidden_imports:
        cmd.extend(["--hidden-import", h])

    # Modulos pesados innecesarios a excluir
    excludes = [
        "onnxruntime",
        "pymupdf_layout",
        "pymupdf4llm",
        "scipy",
        "numpy",
        "pandas",
        "matplotlib",
        "tkinter",
        "tcl",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtNetwork",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtLocation",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSql",
        "PySide6.QtSvg",
        "PySide6.QtTest",
        "PySide6.Qt3DCore",
    ]
    for ex in excludes:
        cmd.extend(["--exclude-module", ex])

    cmd.append(str(root / "run.py"))

    print("[LimeRadial] Ejecutando PyInstaller con exclusiones de modulos...")
    ret = subprocess.run(cmd)
    if ret.returncode == 0:
        dist_dir = root / "dist" / "LimeRadial"
        if dist_dir.exists():
            post_clean_dist(dist_dir)
            dist_exe = dist_dir / "LimeRadial.exe"
        else:
            dist_exe = root / "dist" / "LimeRadial.exe"
        print(f"[LimeRadial] Compilacion optimizada completada con exito en: {dist_exe}")
        return True
    else:
        print("[LimeRadial] Error en la compilacion con PyInstaller.", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
