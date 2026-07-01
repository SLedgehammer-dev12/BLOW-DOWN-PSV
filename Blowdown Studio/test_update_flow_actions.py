import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from update_flow_actions import prompt_and_start_update_download, start_update_check_async


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self._target = target
        self.daemon = daemon

    def start(self):
        self._target()


class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, message):
        self.errors.append(message)


def test_prompt_and_start_update_download_success():
    started = []

    result = prompt_and_start_update_download(
        current_version="v2.3.1",
        latest_version="v2.3.2",
        release_data={"tag_name": "v2.3.2"},
        prompt_update_download_path_fn=lambda *_args: (r"C:\Temp\update.exe", "https://example.com"),
        start_update_download_fn=lambda release_data, save_path, release_page: started.append((release_data, save_path, release_page)),
    )

    assert result == r"C:\Temp\update.exe"
    assert started and started[0][1].endswith("update.exe")


def test_start_update_check_async_update_available():
    scheduled = []

    start_update_check_async(
        current_version="v2.3.1",
        manual=False,
        fetch_latest_release_fn=lambda: {"tag_name": "v2.3.2"},
        is_update_available_fn=lambda current, latest: current != latest,
        schedule_ui_fn=lambda callback: scheduled.append(callback) or callback(),
        prompt_update_fn=lambda latest, data: scheduled.append(("prompt", latest, data["tag_name"])),
        show_up_to_date_fn=lambda: scheduled.append("uptodate"),
        show_connection_error_fn=lambda: scheduled.append("connerr"),
        logger=DummyLogger(),
        thread_factory=ImmediateThread,
    )

    assert ("prompt", "v2.3.2", "v2.3.2") in scheduled


def test_start_update_check_async_manual_error():
    scheduled = []
    logger = DummyLogger()

    start_update_check_async(
        current_version="v2.3.1",
        manual=True,
        fetch_latest_release_fn=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        is_update_available_fn=lambda *_args: False,
        schedule_ui_fn=lambda callback: scheduled.append(callback) or callback(),
        prompt_update_fn=lambda *_args: scheduled.append("prompt"),
        show_up_to_date_fn=lambda: scheduled.append("uptodate"),
        show_connection_error_fn=lambda: scheduled.append("connerr"),
        logger=logger,
        thread_factory=ImmediateThread,
    )

    assert "connerr" in scheduled
    assert logger.errors


if __name__ == "__main__":
    test_prompt_and_start_update_download_success()
    test_start_update_check_async_update_available()
    test_start_update_check_async_manual_error()
    print("TEST COMPLETED")
