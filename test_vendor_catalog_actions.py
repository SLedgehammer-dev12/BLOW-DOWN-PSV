import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from vendor_catalog_actions import (
    format_vendor_catalog_loaded_message,
    format_vendor_catalog_summary_message,
    get_active_vendor_catalog,
    get_active_vendor_catalog_summary,
)


def test_get_active_vendor_catalog_builtin():
    catalog = get_active_vendor_catalog(None)
    assert len(catalog) > 0


def test_get_active_vendor_catalog_summary_builtin():
    summary = get_active_vendor_catalog_summary(None)
    assert summary["model_count"] > 0
    assert len(summary["manufacturers"]) > 0
    assert "exact_metadata_counts" in summary


def test_vendor_catalog_message_formatters():
    summary = {
        "catalog_name": "Demo Catalog",
        "model_count": 3,
        "manufacturers": ["A", "B"],
        "exact_metadata_counts": {
            "trim_code": 1,
            "set_pressure_range": 2,
            "code_stamp": 1,
            "body_material": 2,
            "trim_material": 1,
        },
    }
    loaded = format_vendor_catalog_loaded_message(summary)
    overview = format_vendor_catalog_summary_message(summary)
    assert "Demo Catalog" in loaded
    assert "Model: 3" in loaded
    assert "Toplam model: 3" in overview
    assert "trim=1" in loaded
    assert "materials=2/1" in overview


if __name__ == "__main__":
    test_get_active_vendor_catalog_builtin()
    test_get_active_vendor_catalog_summary_builtin()
    test_vendor_catalog_message_formatters()
    print("TEST COMPLETED")
