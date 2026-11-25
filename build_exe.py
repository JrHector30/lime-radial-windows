"""
Script de compilación para generar el ejecutable autónomo LimeRadial.exe
utilizando PyInstaller.
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


def build():
    root = Path(__file__).resolve().parent
    print("[LimeRadial] Iniciando empaquetado de Lime Radial Windows...")

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

    cmd.append(str(root / "run.py"))

    print("[LimeRadial] Ejecutando PyInstaller...")
    ret = subprocess.run(cmd)
    if ret.returncode == 0:
        dist_exe = root / "dist" / "LimeRadial" / "LimeRadial.exe"
        if not dist_exe.exists():
            dist_exe = root / "dist" / "LimeRadial.exe"
        print(f"[LimeRadial] Compilacion completada con exito en: {dist_exe}")
        return True
    else:
        print("[LimeRadial] Error en la compilacion con PyInstaller.", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
