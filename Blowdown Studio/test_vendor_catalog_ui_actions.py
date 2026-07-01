import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from vendor_catalog_ui_actions import (
    import_vendor_catalog_dialog,
    reset_vendor_catalog_dialog,
    show_vendor_catalog_summary_dialog,
)


def test_import_vendor_catalog_dialog_success():
    infos = []
    errors = []

    file_path = import_vendor_catalog_dialog(
        askopenfilename_fn=lambda **kwargs: r"C:\Temp\catalog.json",
        load_with_summary_fn=lambda path: ({}, {"catalog_name": "Demo", "model_count": 3, "manufacturers": ["A"]}),
        format_loaded_message_fn=lambda summary: f"{summary['catalog_name']} loaded",
        showinfo_fn=lambda title, msg: infos.append((title, msg)),
        showerror_fn=lambda title, msg: errors.append((title, msg)),
    )

    assert file_path == r"C:\Temp\catalog.json"
    assert infos and infos[0][1] == "Demo loaded"
    assert not errors


def test_import_vendor_catalog_dialog_cancel():
    file_path = import_vendor_catalog_dialog(
        askopenfilename_fn=lambda **kwargs: "",
        load_with_summary_fn=lambda path: ({}, {}),
        format_loaded_message_fn=lambda summary: "",
        showinfo_fn=lambda title, msg: None,
        showerror_fn=lambda title, msg: None,
    )
    assert file_path is None


def test_reset_vendor_catalog_dialog():
    infos = []
    result = reset_vendor_catalog_dialog(showinfo_fn=lambda title, msg: infos.append((title, msg)))
    assert result is None
    assert infos


def test_show_vendor_catalog_summary_dialog_success():
    infos = []
    errors = []
    summary = show_vendor_catalog_summary_dialog(
        "demo.json",
        get_summary_fn=lambda path: {"catalog_name": "Demo", "model_count": 2, "manufacturers": ["A", "B"]},
        format_summary_message_fn=lambda summary: f"{summary['catalog_name']} summary",
        showinfo_fn=lambda title, msg: infos.append((title, msg)),
        showerror_fn=lambda title, msg: errors.append((title, msg)),
    )
    assert summary["catalog_name"] == "Demo"
    assert infos and infos[0][1] == "Demo summary"
    assert not errors


if __name__ == "__main__":
    test_import_vendor_catalog_dialog_success()
    test_import_vendor_catalog_dialog_cancel()
    test_reset_vendor_catalog_dialog()
    test_show_vendor_catalog_summary_dialog_success()
    print("TEST COMPLETED")
