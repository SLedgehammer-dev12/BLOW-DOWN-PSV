from __future__ import annotations

import threading


def prompt_and_start_update_download(
    *,
    current_version: str,
    latest_version: str,
    release_data: dict,
    prompt_update_download_path_fn,
    start_update_download_fn,
):
    save_path, release_page = prompt_update_download_path_fn(current_version, latest_version, release_data)
    if not save_path:
        return None
    start_update_download_fn(release_data, save_path, release_page)
    return save_path


def start_update_check_async(
    *,
    current_version: str,
    manual: bool,
    fetch_latest_release_fn,
    is_update_available_fn,
    schedule_ui_fn,
    prompt_update_fn,
    show_up_to_date_fn,
    show_connection_error_fn,
    logger,
    thread_factory=threading.Thread,
):
    def _check():
        try:
            data = fetch_latest_release_fn()
            latest_version = data.get("tag_name", "")

            if is_update_available_fn(current_version, latest_version):
                schedule_ui_fn(lambda: prompt_update_fn(latest_version, data))
            elif manual:
                schedule_ui_fn(show_up_to_date_fn)
        except Exception as exc:
            logger.error(f"Updates fetch failed: {exc}")
            if manual:
                schedule_ui_fn(show_connection_error_fn)

    worker = thread_factory(target=_check, daemon=True)
    worker.start()
    return worker
