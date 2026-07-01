from __future__ import annotations

import logging
import threading
from tkinter import messagebox

from update_actions import download_release_asset


def prompt_update_download_path(
    current_version: str,
    latest_version: str,
    release_data: dict,
    *,
    default_path_fn,
    choose_path_fn,
    askyesnocancel_fn=messagebox.askyesnocancel,
    showwarning_fn=messagebox.showwarning,
):
    release_page = release_data.get("html_url", "")
    ans = askyesnocancel_fn(
        "Yeni Surum Bulundu",
        f"Programin yeni bir surumu yayimlanmis!\n"
        f"Mevcut: {current_version} -> Yeni: {latest_version}\n\n"
        "Evet: Varsayilan Indirilenler klasorune indir\n"
        "Hayir: Kayit konumunu sen sec\n"
        "Iptal: Indirmeden cik",
    )
    if ans is None:
        return None, release_page

    if ans is False:
        try:
            save_path = choose_path_fn(release_data)
        except ValueError:
            showwarning_fn("Güncelleme", "İndirilebilir dosya bulunamadı.")
            return None, release_page
    else:
        save_path = default_path_fn(release_data)
        if not save_path:
            showwarning_fn("Güncelleme", "İndirilebilir dosya bulunamadı.")
            return None, release_page

    return save_path, release_page


def start_update_download_async(
    release_data: dict,
    save_path: str,
    *,
    schedule_ui,
    set_progress_text,
    show_info,
    show_error,
    download_fn=download_release_asset,
    logger=None,
    thread_factory=threading.Thread,
):
    if logger is None:
        logger = logging.getLogger(__name__)

    def _download():
        try:
            download_fn(
                release_data,
                save_path,
                progress_callback=lambda pct: schedule_ui(lambda p=pct: set_progress_text(f"Güncelleme indiriliyor... %{p:.1f}")),
            )
            logger.info("Güncelleme dosyası indirildi: %s", save_path)
            schedule_ui(lambda: show_info("Güncelleme", f"Yeni sürüm indirildi:\n{save_path}"))
            schedule_ui(lambda: set_progress_text("Güncelleme indirildi."))
        except Exception as exc:
            logger.error("Update download failed: %s", exc)
            schedule_ui(lambda e=exc: show_error("Güncelleme", f"Güncelleme indirilemedi:\n{e}"))
            schedule_ui(lambda: set_progress_text("Güncelleme indirilemedi."))

    set_progress_text("Güncelleme indiriliyor...")
    worker = thread_factory(target=_download, daemon=True)
    worker.start()
    return worker
