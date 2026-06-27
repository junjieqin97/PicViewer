# Continuous Integration

PicViewer uses GitHub Actions for desktop installer validation and release
automation. The release workflow builds native macOS and Windows desktop
installers. Release-branch runs also publish both platforms to one GitHub
Release.

## Desktop Release Automation

The desktop release workflow is defined in
`.github/workflows/release-desktop.yml`. It has two merge-driven modes:

- Develop validation: when a pull request from a same-repository branch is
  merged into `develop`, the workflow builds and verifies the macOS DMG and
  Windows MSI, then uploads them as workflow artifacts. It does not create a
  GitHub Release.
- Release publishing: when a pull request from `develop` is merged into a
  `release-*` branch, such as `release-0.1.0`, the workflow builds and
  verifies both installers, uploads them as workflow artifacts, and publishes
  one GitHub Release.

Closed pull requests that are not merged, pull requests from forks, and pull
requests into `release-*` branches from branches other than `develop` do not
run the desktop installer jobs.

The workflow uses separate platform runners because PicViewer packaging does
not support cross-building:

- The macOS job runs on `macos-15`. This GitHub-hosted runner is an
  Apple Silicon machine, so the macOS release artifact is an arm64 DMG.
  Intel x64 and universal macOS builds are out of scope for this workflow.
- The Windows job runs on `windows-2025` and builds an x64 MSI from the
  Windows PyInstaller onedir app.

## Build Steps

The workflow has four jobs:

- `release-metadata` checks out the target branch, reads `project.version`
  from `pyproject.toml`, computes release asset names, and records whether the
  run should publish a GitHub Release. Release publishing runs fail early if
  the GitHub Release tag already exists; develop validation runs skip that
  release-existence check.
- `build-macos` recreates the macOS packaging environment, runs the unit test
  suite, builds `dist/PicViewer.app`, builds `dist/PicViewer-<version>.dmg`,
  verifies `dist/PicViewer-<version>.dmg.sha256`, and uploads the DMG assets
  as workflow artifacts.
- `build-windows` recreates the Windows packaging environment, installs WiX,
  runs the unit test suite, builds `dist/PicViewer/`, builds
  `dist/PicViewer-<version>.msi`, verifies
  `dist/PicViewer-<version>.msi.sha256`, and uploads the MSI assets as
  workflow artifacts.
- `publish-release` downloads both platform artifact sets and creates one
  GitHub Release containing all release assets. This job runs only for
  `develop` to `release-*` merges.

The packaging scripts remain the source of truth for generating the app
bundle, DMG, and MSI. The workflow only orchestrates those scripts in GitHub
Actions.

The release jobs pin Qt/PySide6 to `6.11.1` through `QT_RUNTIME_VERSION`,
pyvips to `3.1.1` through `PYVIPS_VERSION`, libvips to `8.18.2` through
`LIBVIPS_VERSION`, and rawpy to `0.27.0` through `RAWPY_VERSION`. Dependency
installation follows a conda-forge-first policy through
`scripts/packaging/install_release_dependencies.py`: conda-forge provides
Qt/PySide6, OpenCV, numpy, pyvips/libvips, Pillow, Pillow AVIF/HEIF plugins,
rawpy, PyInstaller, twine, and Python build tooling. PyPI is used only for the
explicit `pyexiv2` fallback, then PicViewer itself is installed with
`python -m pip install -e . --no-deps` so pip cannot replace conda-forge
packages. After dependency installation,
`scripts/packaging/verify_dependency_sources.py` checks the conda/PyPI source
split, and `scripts/packaging/verify_pyvips_runtime.py` checks pyvips metadata
and libvips/LittleCMS native files. Keeping the native Qt runtime,
pyvips/libvips CMS backend, and packaged RAW backend stable across GitHub
runner image updates reduces release-only failures in headless unit tests and
PyInstaller packaging.

## Windows WiX EULA Handling

The Windows job installs WiX with the .NET SDK and runs:

```bash
python scripts/packaging/build_msi.py --accept-wix-eula
```

The `--accept-wix-eula` flag passes `-acceptEula wix7` to WiX. This CI
configuration is intentional and should only be kept enabled while the project
maintainer accepts the WiX v7 OSMF EULA requirements documented in
`docs/packaging.md`.

## Version and Release Tag

The release version comes from `pyproject.toml` at `project.version`. The
workflow publishes tag `v<version>` and uploads these assets:

- `PicViewer-<version>.dmg`
- `PicViewer-<version>.dmg.sha256`
- `PicViewer-<version>.msi`
- `PicViewer-<version>.msi.sha256`

For example, version `0.1.0` publishes GitHub Release tag `v0.1.0` with
`PicViewer-0.1.0.dmg`, `PicViewer-0.1.0.dmg.sha256`,
`PicViewer-0.1.0.msi`, and `PicViewer-0.1.0.msi.sha256`.

## Re-running Workflows

Develop validation runs can be re-run from GitHub Actions without changing the
project version because they do not create or check for a GitHub Release.

The release publishing workflow does not overwrite an existing GitHub Release
or existing release assets. If a release for `v<version>` already exists, the
job fails and the project version must be bumped before the release is run
again.

This workflow does not perform code signing, notarization, PyPI upload, Linux
packaging, auto-update setup, or telemetry.
