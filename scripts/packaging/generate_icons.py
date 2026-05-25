"""Generate PicViewer icon assets from the SVG master."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image
from PySide6 import QtCore, QtGui, QtSvg

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ICON_DIR = PROJECT_ROOT / "src" / "pic_viewer" / "ui" / "resources" / "icons"
PACKAGING_ICON_DIR = PROJECT_ROOT / "packaging" / "icons"
BUILD_ICON_DIR = PROJECT_ROOT / "build" / "icons"
SVG_PATH = RUNTIME_ICON_DIR / "picviewer.svg"
PNG_SIZES = (16, 32, 48, 64, 128, 256, 512, 1024)


def render_png(size: int) -> Path:
    """Render the SVG master to a square PNG of the requested size."""

    renderer = QtSvg.QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG icon source: {SVG_PATH}")

    image = QtGui.QImage(size, size, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()

    output_path = RUNTIME_ICON_DIR / f"picviewer-{size}.png"
    if not image.save(str(output_path), "PNG"):
        raise RuntimeError(f"Failed to write PNG icon: {output_path}")
    return output_path


def generate_pngs() -> list[Path]:
    """Generate all runtime PNG icon sizes."""

    RUNTIME_ICON_DIR.mkdir(parents=True, exist_ok=True)
    return [render_png(size) for size in PNG_SIZES]


def generate_ico(png_paths: list[Path]) -> Path:
    """Generate the Windows ICO asset from rendered PNGs."""

    PACKAGING_ICON_DIR.mkdir(parents=True, exist_ok=True)
    source = Image.open(RUNTIME_ICON_DIR / "picviewer-1024.png").convert("RGBA")
    output_path = PACKAGING_ICON_DIR / "picviewer.ico"
    source.save(
        output_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    source.close()
    return output_path


def generate_icns() -> Path:
    """Generate the macOS ICNS asset using iconutil."""

    iconset_dir = BUILD_ICON_DIR / "PicViewer.iconset"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True)

    iconset_files = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for file_name, size in iconset_files.items():
        shutil.copy2(RUNTIME_ICON_DIR / f"picviewer-{size}.png", iconset_dir / file_name)

    output_path = PACKAGING_ICON_DIR / "picviewer.icns"
    if output_path.exists():
        output_path.unlink()
    iconutil = shutil.which("iconutil")
    if iconutil is not None:
        try:
            subprocess.run(
                [iconutil, "--convert", "icns", "--output", str(output_path), str(iconset_dir)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return output_path
        except subprocess.CalledProcessError:
            pass

    source = Image.open(RUNTIME_ICON_DIR / "picviewer-1024.png").convert("RGBA")
    source.save(
        output_path,
        format="ICNS",
        sizes=[(16, 16), (32, 32), (128, 128), (256, 256), (512, 512), (1024, 1024)],
    )
    source.close()
    return output_path


def main() -> None:
    """Generate all runtime and platform icon assets."""

    png_paths = generate_pngs()
    ico_path = generate_ico(png_paths)
    icns_path = generate_icns()
    print(f"Generated {len(png_paths)} PNG icons")
    print(f"Generated {ico_path}")
    print(f"Generated {icns_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(str(exc)) from exc
