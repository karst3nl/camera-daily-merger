from importlib.metadata import version

from camera_daily_merger import __version__


def test_installed_package_version():
    assert version("camera-daily-merger") == __version__
