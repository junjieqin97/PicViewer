# Continuous Integration

PicViewer uses GitHub Actions for release automation. The initial CI release
workflow only builds the macOS desktop artifact and publishes it to GitHub
Releases.

## macOS Release Automation

The macOS release workflow is defined in
`.github/workflows/release-macos.yml`. It runs when a pull request from
`develop` is merged into a `release-*` branch, such as `release-0.1.0`.
Closed pull requests that are not merged, pull requests from other branches,
and pull requests from forks do not publish a release.

The workflow runs on the `macos-15` GitHub-hosted runner. This runner is an
Apple Silicon machine, so the initial release artifact is an arm64 DMG. Intel
x64 and universal macOS builds are out of scope for the initial workflow.

## Build Steps

The workflow recreates the packaging environment used by the local release
scripts:

- Create and activate the `PicViewer` conda environment with Python 3.10.
- Install the native `inih` library required by the packaged `pyexiv2` runtime.
- Install PySide2 from conda-forge so Qt tools such as `lrelease` are available.
- Install the project with the `packaging` extra.
- Run the unit test suite.
- Build `dist/PicViewer.app`.
- Build `dist/PicViewer-<version>.dmg`.
- Verify `dist/PicViewer-<version>.dmg.sha256`.

The packaging scripts remain the source of truth for generating the app bundle
and DMG. The workflow only orchestrates those scripts in GitHub Actions.

## Version and Release Tag

The release version comes from `pyproject.toml` at `project.version`. The
workflow publishes tag `v<version>` and uploads these assets:

- `PicViewer-<version>.dmg`
- `PicViewer-<version>.dmg.sha256`

For example, version `0.1.0` publishes GitHub Release tag `v0.1.0` with
`PicViewer-0.1.0.dmg` and `PicViewer-0.1.0.dmg.sha256`.

## Re-running Releases

The workflow does not overwrite an existing GitHub Release or existing release
assets. If a release for `v<version>` already exists, the job fails and the
project version must be bumped before the release is run again.

This workflow does not perform code signing, notarization, PyPI upload,
Windows packaging, Linux packaging, auto-update setup, or telemetry.
