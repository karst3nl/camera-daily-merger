from importlib.metadata import version

from camera_daily_merger import __version__


def test_installed_package_version():
    assert version("camera-daily-merger") == __version__


def test_addon_license_and_notices_match_repository():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    assert (root / "LICENSE").read_bytes() == (
        root / "camera_daily_merger/LICENSE"
    ).read_bytes()
    assert (root / "docs/THIRD_PARTY.md").read_bytes() == (
        root / "camera_daily_merger/THIRD_PARTY.md"
    ).read_bytes()


def test_addon_runtime_and_package_versions_agree():
    from pathlib import Path
    import tomllib

    from camera_daily_merger.app import APP_VERSION

    root = Path(__file__).resolve().parents[2]
    config = (root / "camera_daily_merger/config.yaml").read_text()
    assert f"\nversion: {APP_VERSION}\n" in config
    assert APP_VERSION == __version__ == version("camera-daily-merger")
    metadata = tomllib.loads((root / "pyproject.toml").read_text())
    assert metadata["project"]["dynamic"] == ["version"]
