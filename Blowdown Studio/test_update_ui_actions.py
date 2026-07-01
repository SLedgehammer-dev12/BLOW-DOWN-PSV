import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from update_ui_actions import prompt_update_download_path, start_update_download_async


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self._target = target
        self.daemon = daemon

    def start(self):
        self._target()


def test_prompt_update_download_path_default():
    save_path, release_page = prompt_update_download_path(
        "v2.3.1",
        "v2.3.2",
        {"html_url": "https://example.com/release"},
        default_path_fn=lambda data: r"C:\Temp\update.exe",
        choose_path_fn=lambda data: r"C:\Other\update.exe",
        askyesnocancel_fn=lambda *args, **kwargs: True,
    )
    assert save_path == r"C:\Temp\update.exe"
    assert release_page == "https://example.com/release"


def test_prompt_update_download_path_custom():
    save_path, release_page = prompt_update_download_path(
        "v2.3.1",
        "v2.3.2",
        {"html_url": "https://example.com/release"},
        default_path_fn=lambda data: r"C:\Temp\update.exe",
        choose_path_fn=lambda data: r"C:\Custom\update.exe",
        askyesnocancel_fn=lambda *args, **kwargs: False,
    )
    assert save_path == r"C:\Custom\update.exe"
    assert release_page == "https://example.com/release"


def test_prompt_update_download_path_cancel():
    save_path, release_page = prompt_update_download_path(
        "v2.3.1",
        "v2.3.2",
        {"html_url": "https://example.com/release"},
        default_path_fn=lambda data: r"C:\Temp\update.exe",
        choose_path_fn=lambda data: r"C:\Custom\update.exe",
        askyesnocancel_fn=lambda *args, **kwargs: None,
    )
    assert save_path is None
    assert release_page == "https://example.com/release"


def test_start_update_download_async_success():
    scheduled = []
    progress_messages = []
    infos = []
    errors = []

    def schedule_ui(callback, *args):
        if callable(callback):
            scheduled.append("callback")
            callback()

    def fake_download(release_data, save_path, progress_callback=None):
        assert release_data["tag_name"] == "v2.3.2"
        assert save_path.endswith("update.exe")
        if progress_callback is not None:
            progress_callback(42.0)
        return save_path

    start_update_download_async(
        {"tag_name": "v2.3.2"},
        r"C:\Temp\update.exe",
        schedule_ui=schedule_ui,
        set_progress_text=progress_messages.append,
        show_info=lambda title, msg: infos.append((title, msg)),
        show_error=lambda title, msg: errors.append((title, msg)),
        download_fn=fake_download,
        thread_factory=ImmediateThread,
    )

    assert progress_messages[0] == "Güncelleme indiriliyor..."
    assert any("%42.0" in msg for msg in progress_messages)
    assert progress_messages[-1] == "Güncelleme indirildi."
    assert infos and not errors


if __name__ == "__main__":
    test_prompt_update_download_path_default()
    test_prompt_update_download_path_custom()
    test_prompt_update_download_path_cancel()
    test_start_update_download_async_success()
    print("TEST COMPLETED")
