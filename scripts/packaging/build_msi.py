"""Build a Windows MSI installer from the existing PicViewer onedir app."""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable, Mapping, Optional, Sequence
import uuid
import xml.etree.ElementTree as ET

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.9/3.10.
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

logger = logging.getLogger(__name__)

EXPECTED_CONDA_ENV = "PicViewer"
APP_NAME = "PicViewer"
MANUFACTURER = "PicViewer Team"
PRODUCT_UPGRADE_CODE = "{E85C5722-4F09-5B7E-A7F2-76B6273E9C23}"
WIX_NAMESPACE = "http://wixtoolset.org/schemas/v4/wxs"
WIX_GUID_NAMESPACE = uuid.UUID("d79067c6-0ac7-5cb8-9d91-d015fa6b615c")
WIX_EULA_ID = "wix7"
WIX_OSMF_URL = "https://wixtoolset.org/osmf/"

ET.register_namespace("", WIX_NAMESPACE)


def project_root() -> Path:
    """Return the repository root for this script."""

    return Path(__file__).resolve().parents[2]


def ensure_conda_environment(env: Optional[Mapping[str, str]] = None) -> None:
    """Ensure MSI packaging runs inside the PicViewer conda environment."""

    current_env = (os.environ if env is None else env).get("CONDA_DEFAULT_ENV")
    if current_env != EXPECTED_CONDA_ENV:
        raise RuntimeError(
            f"Activate the {EXPECTED_CONDA_ENV} conda environment before packaging "
            f"(current: {current_env or 'not set'})."
        )


def ensure_windows(platform: str = sys.platform) -> None:
    """Ensure the MSI build is running on Windows."""

    if platform != "win32":
        raise RuntimeError("MSI packaging is only supported on Windows.")


def ensure_wix_executable(
    wix_executable: str,
    path_lookup: Callable[[str], Optional[str]] = shutil.which,
) -> None:
    """Ensure the WiX command-line tool can be found before building."""

    if path_lookup(wix_executable) is None:
        raise RuntimeError(
            "Cannot find WiX CLI. Install WiX Toolset and ensure 'wix' is on PATH, "
            "or pass --wix with the path to wix.exe."
        )


def read_project_version(pyproject_path: Path) -> str:
    """Read the MSI-compatible project version from pyproject.toml."""

    with pyproject_path.open("rb") as file_obj:
        pyproject = tomllib.load(file_obj)

    version = pyproject.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"Cannot read project.version from {pyproject_path}.")
    return validate_msi_version(version)


def validate_msi_version(version: str) -> str:
    """Validate that a version can be used as a Windows Installer ProductVersion."""

    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise RuntimeError(
            f"MSI ProductVersion must use MAJOR.MINOR.PATCH numeric format: {version}."
        )
    return version


def ensure_app_directory(app_dir: Path) -> None:
    """Ensure the PyInstaller onedir app exists before creating an MSI."""

    exe_path = app_dir / f"{APP_NAME}.exe"
    if not app_dir.is_dir() or not exe_path.is_file():
        raise RuntimeError(
            f"Missing Windows app directory: {app_dir}. "
            "Run python scripts/packaging/build_app.py first."
        )


def wix_tag(name: str) -> str:
    """Return a WiX XML tag name with the default namespace."""

    return f"{{{WIX_NAMESPACE}}}{name}"


def stable_guid(name: str) -> str:
    """Return a deterministic uppercase GUID for a WiX component."""

    return "{" + str(uuid.uuid5(WIX_GUID_NAMESPACE, name)).upper() + "}"


def stable_id(prefix: str, name: str) -> str:
    """Return a deterministic WiX identifier for a generated item."""

    return f"{prefix}_{uuid.uuid5(WIX_GUID_NAMESPACE, name).hex}"


def wix_source_path(relative_path: Path) -> str:
    """Return a WiX source path using the AppSourceDir preprocessor variable."""

    return "$(var.AppSourceDir)\\" + "\\".join(relative_path.parts)


def collect_app_files(app_dir: Path) -> list[Path]:
    """Collect files from the PyInstaller onedir app in deterministic order."""

    return sorted(
        (path for path in app_dir.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(app_dir).as_posix().casefold(),
    )


def add_directory(
    parent: ET.Element,
    directory_nodes: dict[tuple[str, ...], ET.Element],
    parts: tuple[str, ...],
) -> ET.Element:
    """Add or return a generated Directory element for a relative directory."""

    if parts in directory_nodes:
        return directory_nodes[parts]

    parent_parts = parts[:-1]
    parent_node = add_directory(parent, directory_nodes, parent_parts)
    relative_name = "/".join(parts)
    directory_node = ET.SubElement(
        parent_node,
        wix_tag("Directory"),
        {"Id": stable_id("Dir", relative_name), "Name": parts[-1]},
    )
    directory_nodes[parts] = directory_node
    return directory_node


def add_application_files(
    package: ET.Element,
    install_dir: ET.Element,
    app_dir: Path,
) -> None:
    """Add all PyInstaller app files as one-file WiX components."""

    component_group = ET.SubElement(package, wix_tag("ComponentGroup"), {"Id": "ApplicationFiles"})
    directory_nodes: dict[tuple[str, ...], ET.Element] = {(): install_dir}

    for file_path in collect_app_files(app_dir):
        relative_path = file_path.relative_to(app_dir)
        relative_key = relative_path.as_posix()
        directory_node = add_directory(install_dir, directory_nodes, relative_path.parts[:-1])
        component_id = stable_id("Component", relative_key)
        file_id = stable_id("File", relative_key)
        component = ET.SubElement(
            directory_node,
            wix_tag("Component"),
            {"Id": component_id, "Guid": stable_guid(f"component:{relative_key}")},
        )
        ET.SubElement(
            component,
            wix_tag("File"),
            {
                "Id": file_id,
                "Source": wix_source_path(relative_path),
                "KeyPath": "yes",
            },
        )
        ET.SubElement(component_group, wix_tag("ComponentRef"), {"Id": component_id})


def add_shortcut_components(package: ET.Element) -> None:
    """Add Start Menu and Desktop shortcuts to the installed application."""

    shortcut_attrs = {
        "Name": APP_NAME,
        "Description": "PicViewer desktop photo viewer",
        "Target": f"[INSTALLFOLDER]{APP_NAME}.exe",
        "WorkingDirectory": "INSTALLFOLDER",
        "Icon": "PicViewerIcon.exe",
    }

    start_menu_component = ET.SubElement(
        package,
        wix_tag("Component"),
        {
            "Id": "StartMenuShortcutComponent",
            "Directory": "ApplicationProgramsFolder",
            "Guid": stable_guid("shortcut:start-menu"),
        },
    )
    ET.SubElement(
        start_menu_component,
        wix_tag("Shortcut"),
        {"Id": "StartMenuShortcut", **shortcut_attrs},
    )
    ET.SubElement(
        start_menu_component,
        wix_tag("RemoveFolder"),
        {
            "Id": "RemoveApplicationProgramsFolder",
            "Directory": "ApplicationProgramsFolder",
            "On": "uninstall",
        },
    )
    add_shortcut_registry_key(start_menu_component, "StartMenuShortcut")

    desktop_component = ET.SubElement(
        package,
        wix_tag("Component"),
        {
            "Id": "DesktopShortcutComponent",
            "Directory": "DesktopFolder",
            "Guid": stable_guid("shortcut:desktop"),
        },
    )
    ET.SubElement(
        desktop_component,
        wix_tag("Shortcut"),
        {"Id": "DesktopShortcut", **shortcut_attrs},
    )
    add_shortcut_registry_key(desktop_component, "DesktopShortcut")


def add_shortcut_registry_key(component: ET.Element, name: str) -> None:
    """Add a registry key path for a shortcut-only component."""

    ET.SubElement(
        component,
        wix_tag("RegistryValue"),
        {
            "Root": "HKLM",
            "Key": rf"Software\{APP_NAME}",
            "Name": name,
            "Type": "integer",
            "Value": "1",
            "KeyPath": "yes",
        },
    )


def add_feature(package: ET.Element) -> None:
    """Add the main MSI feature and component references."""

    feature = ET.SubElement(
        package,
        wix_tag("Feature"),
        {"Id": "MainFeature", "Title": APP_NAME, "Level": "1"},
    )
    ET.SubElement(feature, wix_tag("ComponentGroupRef"), {"Id": "ApplicationFiles"})
    ET.SubElement(feature, wix_tag("ComponentRef"), {"Id": "StartMenuShortcutComponent"})
    ET.SubElement(feature, wix_tag("ComponentRef"), {"Id": "DesktopShortcutComponent"})


def write_wix_source(root: Path, app_dir: Path, version: str) -> Path:
    """Generate a WiX source file that installs the PyInstaller onedir app."""

    msi_build_dir = root / "build" / "msi"
    msi_build_dir.mkdir(parents=True, exist_ok=True)
    wxs_path = msi_build_dir / f"{APP_NAME}.wxs"

    wix = ET.Element(wix_tag("Wix"))
    package = ET.SubElement(
        wix,
        wix_tag("Package"),
        {
            "Name": APP_NAME,
            "Manufacturer": MANUFACTURER,
            "Version": version,
            "UpgradeCode": PRODUCT_UPGRADE_CODE,
            "Scope": "perMachine",
        },
    )
    ET.SubElement(
        package,
        wix_tag("MajorUpgrade"),
        {"DowngradeErrorMessage": "A newer version of PicViewer is already installed."},
    )
    ET.SubElement(package, wix_tag("MediaTemplate"), {"EmbedCab": "yes", "CompressionLevel": "high"})
    ET.SubElement(
        package,
        wix_tag("Icon"),
        {"Id": "PicViewerIcon.exe", "SourceFile": r"$(var.ProjectRoot)\packaging\icons\picviewer.ico"},
    )
    ET.SubElement(package, wix_tag("Property"), {"Id": "ARPPRODUCTICON", "Value": "PicViewerIcon.exe"})

    program_files_dir = ET.SubElement(package, wix_tag("StandardDirectory"), {"Id": "ProgramFiles64Folder"})
    install_dir = ET.SubElement(program_files_dir, wix_tag("Directory"), {"Id": "INSTALLFOLDER", "Name": APP_NAME})
    start_menu_dir = ET.SubElement(package, wix_tag("StandardDirectory"), {"Id": "ProgramMenuFolder"})
    ET.SubElement(start_menu_dir, wix_tag("Directory"), {"Id": "ApplicationProgramsFolder", "Name": APP_NAME})
    ET.SubElement(package, wix_tag("StandardDirectory"), {"Id": "DesktopFolder"})

    add_application_files(package, install_dir, app_dir)
    add_shortcut_components(package)
    add_feature(package)

    tree = ET.ElementTree(wix)
    ET.indent(tree, space="  ")
    tree.write(wxs_path, encoding="utf-8", xml_declaration=True)
    logger.info("WiX source written to: %s", wxs_path)
    return wxs_path


def write_sha256_checksum(msi_path: Path) -> Path:
    """Write a SHA256 checksum file next to a generated MSI."""

    checksum_path = msi_path.with_name(f"{msi_path.name}.sha256")
    sha256 = hashlib.sha256()

    try:
        with msi_path.open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                sha256.update(chunk)

        checksum_path.write_text(
            f"{sha256.hexdigest()}  {msi_path.name}\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise RuntimeError(f"Cannot write SHA256 checksum for MSI: {msi_path}.") from exc

    logger.info("SHA256 checksum written to: %s", checksum_path)
    return checksum_path


def build_wix_command(
    wix_executable: str,
    app_dir: Path,
    project_root: Path,
    intermediate_dir: Path,
    msi_path: Path,
    wxs_path: Path,
    accept_wix_eula: bool = False,
) -> list[str]:
    """Build the WiX CLI command used to create the MSI."""

    command = [wix_executable, "build"]
    if accept_wix_eula:
        command.extend(["-acceptEula", WIX_EULA_ID])

    command.extend(
        [
            "-arch",
            "x64",
            "-define",
            f"AppSourceDir={app_dir}",
            "-define",
            f"ProjectRoot={project_root}",
            "-intermediateFolder",
            str(intermediate_dir),
            "-out",
            str(msi_path),
            str(wxs_path),
        ]
    )
    return command


def subprocess_output(exc: subprocess.CalledProcessError) -> str:
    """Return stdout and stderr text captured from a failed subprocess."""

    output_parts: list[str] = []
    for stream in (exc.stdout, exc.stderr):
        if not stream:
            continue
        if isinstance(stream, bytes):
            output_parts.append(stream.decode("utf-8", errors="replace").strip())
        else:
            output_parts.append(str(stream).strip())
    return "\n".join(part for part in output_parts if part)


def format_wix_build_error(exc: subprocess.CalledProcessError) -> str:
    """Return a user-actionable error message for a failed WiX build."""

    output = subprocess_output(exc)
    if "WIX7015" in output or "Open Source Maintenance Fee" in output:
        return (
            "WiX Toolset v7 requires OSMF EULA acceptance before building an MSI. "
            f"Review {WIX_OSMF_URL}, then run 'wix eula accept {WIX_EULA_ID}' once "
            "per user/machine or rerun this script with '--accept-wix-eula'."
            f"\n\nWiX output:\n{output}"
        )

    if output:
        return f"WiX build failed.\n\nWiX output:\n{output}"
    return str(exc)


def run_wix_build(
    command: Sequence[str],
    project_root: Path,
    runner: Callable[..., object] = subprocess.run,
) -> None:
    """Run WiX and convert known failures into actionable RuntimeError messages."""

    try:
        runner(
            list(command),
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(format_wix_build_error(exc)) from exc


def build_msi(
    project_root: Path,
    env: Optional[Mapping[str, str]] = None,
    runner: Callable[..., object] = subprocess.run,
    platform: str = sys.platform,
    wix_executable: str = "wix",
    path_lookup: Callable[[str], Optional[str]] = shutil.which,
    accept_wix_eula: bool = False,
) -> Path:
    """Create a Windows MSI from dist/PicViewer."""

    ensure_conda_environment(env)
    ensure_windows(platform)
    ensure_wix_executable(wix_executable, path_lookup)

    dist_dir = project_root / "dist"
    app_dir = dist_dir / APP_NAME
    ensure_app_directory(app_dir)

    version = read_project_version(project_root / "pyproject.toml")
    msi_path = dist_dir / f"{APP_NAME}-{version}.msi"
    wxs_path = write_wix_source(project_root, app_dir, version)
    intermediate_dir = project_root / "build" / "msi" / "obj"
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    command = build_wix_command(
        wix_executable=wix_executable,
        app_dir=app_dir,
        project_root=project_root,
        intermediate_dir=intermediate_dir,
        msi_path=msi_path,
        wxs_path=wxs_path,
        accept_wix_eula=accept_wix_eula,
    )
    run_wix_build(command, project_root, runner)
    write_sha256_checksum(msi_path)
    return msi_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Build the PicViewer Windows MSI.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root(),
        help="Repository root. Defaults to the current PicViewer checkout.",
    )
    parser.add_argument(
        "--wix",
        default="wix",
        help="WiX CLI executable. Defaults to wix on PATH.",
    )
    parser.add_argument(
        "--accept-wix-eula",
        action="store_true",
        help=(
            "Pass '-acceptEula wix7' to WiX. Use only after reviewing the WiX "
            "OSMF EULA requirements."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the MSI build command."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    try:
        msi_path = build_msi(
            args.project_root.resolve(),
            wix_executable=args.wix,
            accept_wix_eula=args.accept_wix_eula,
        )
    except (RuntimeError, subprocess.CalledProcessError, OSError) as exc:
        logger.error("%s", exc)
        return 1

    logger.info("MSI artifact written to: %s", msi_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
