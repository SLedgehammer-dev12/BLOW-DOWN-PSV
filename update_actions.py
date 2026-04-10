from __future__ import annotations

import json
import os
import urllib.request
from tkinter import filedialog


LATEST_RELEASE_URL = "https://api.github.com/repos/SLedgehammer-dev12/BLOW-DOWN-PSV/releases/latest"
USER_AGENT = "Mozilla/5.0"


def version_key(version: str) -> list[int]:
    import re

    nums = [int(n) for n in re.findall(r"\d+", version or "")]
    return nums if nums else [0]


def is_update_available(current_version: str, latest_version: str) -> bool:
    return bool(latest_version) and version_key(latest_version) > version_key(current_version)


def fetch_latest_release(url: str = LATEST_RELEASE_URL) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def select_release_asset(release_data: dict):
    assets = release_data.get("assets", [])
    if not assets:
        return None
    exe_assets = [asset for asset in assets if asset.get("name", "").lower().endswith(".exe")]
    if not exe_assets:
        return assets[0]

    preferred_keywords = (
        "blowdown studio",
        "blowdown_studio",
        "blow down psv",
        "blow_down_psv",
    )
    for keyword in preferred_keywords:
        matched = next((asset for asset in exe_assets if keyword in asset.get("name", "").lower()), None)
        if matched:
            return matched
    return exe_assets[0]


def default_update_download_path(release_data: dict, downloads_dir: str | None = None) -> str | None:
    asset = select_release_asset(release_data)
    if not asset:
        return None
    if downloads_dir is None:
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    return os.path.join(downloads_dir, asset.get("name", f"update_{release_data.get('tag_name', 'latest')}"))


def choose_update_download_path(release_data: dict) -> str:
    asset = select_release_asset(release_data)
    if not asset:
        raise ValueError("İndirilebilir dosya bulunamadı.")
    initial_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    return filedialog.asksaveasfilename(
        title="Güncelleme Dosyasını Kaydet",
        initialdir=initial_dir,
        initialfile=asset.get("name", ""),
        defaultextension=os.path.splitext(asset.get("name", ""))[1] or ".exe",
        filetypes=[("Yürütülebilir Dosya", "*.exe"), ("Tüm Dosyalar", "*.*")],
    )


def download_release_asset(release_data: dict, save_path: str, progress_callback=None) -> str:
    asset = select_release_asset(release_data)
    if not asset:
        raise ValueError("İndirilebilir dosya bulunamadı.")

    download_url = asset.get("browser_download_url")
    if not download_url:
        raise ValueError("İndirme bağlantısı bulunamadı.")

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    req = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as response, open(save_path, "wb") as out_file:
        total_size = int(response.headers.get("Content-Length", "0") or 0)
        downloaded = 0
        chunk_size = 1024 * 256
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if progress_callback is not None and total_size > 0:
                progress_callback(downloaded / total_size * 100.0)
    return save_path
