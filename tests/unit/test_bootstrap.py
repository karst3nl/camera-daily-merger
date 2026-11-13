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
