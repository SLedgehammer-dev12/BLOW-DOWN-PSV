import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from update_actions import (
    default_update_download_path,
    is_update_available,
    select_release_asset,
    version_key,
)


def test_version_key_and_update_compare():
    assert version_key("v2.3.1") == [2, 3, 1]
    assert is_update_available("v2.3.1", "v2.3.2") is True
    assert is_update_available("v2.3.2", "v2.3.2") is False


def test_select_release_asset_prefers_blowdown_studio_exe():
    release_data = {
        "assets": [
            {"name": "notes.txt"},
            {"name": "legacy_tool.exe"},
            {"name": "Blowdown_Studio_v2.3.2.exe"},
        ]
    }
    asset = select_release_asset(release_data)
    assert asset["name"] == "Blowdown_Studio_v2.3.2.exe"


def test_default_update_download_path():
    release_data = {
        "tag_name": "v2.3.2",
        "assets": [{"name": "Blowdown_Studio_v2.3.2.exe"}],
    }
    path = default_update_download_path(release_data, downloads_dir=r"C:\Temp")
    assert path == os.path.join(r"C:\Temp", "Blowdown_Studio_v2.3.2.exe")


if __name__ == "__main__":
    test_version_key_and_update_compare()
    test_select_release_asset_prefers_blowdown_studio_exe()
    test_default_update_download_path()
    print("TEST COMPLETED")
