from __future__ import annotations

from psv_vendor_catalog import load_vendor_catalog, summarize_vendor_catalog


def get_active_vendor_catalog(vendor_catalog_path: str | None):
    if vendor_catalog_path:
        return load_vendor_catalog(vendor_catalog_path)
    return load_vendor_catalog()


def load_vendor_catalog_with_summary(path: str):
    catalog = load_vendor_catalog(path)
    summary = summarize_vendor_catalog(catalog)
    return catalog, summary


def get_active_vendor_catalog_summary(vendor_catalog_path: str | None) -> dict:
    return summarize_vendor_catalog(get_active_vendor_catalog(vendor_catalog_path))


def format_vendor_catalog_loaded_message(summary: dict) -> str:
    exact_counts = summary.get("exact_metadata_counts", {})
    return (
        f"Katalog yuklendi:\n{summary['catalog_name']}\n"
        f"Model: {summary['model_count']}\n"
        f"Uretici: {', '.join(summary['manufacturers'])}\n"
        f"Exact metadata coverage: trim={exact_counts.get('trim_code', 0)}, "
        f"set-pressure={exact_counts.get('set_pressure_range', 0)}, "
        f"stamp={exact_counts.get('code_stamp', 0)}"
    )


def format_vendor_catalog_summary_message(summary: dict) -> str:
    exact_counts = summary.get("exact_metadata_counts", {})
    return (
        f"Katalog: {summary['catalog_name']}\n"
        f"Toplam model: {summary['model_count']}\n"
        f"Ureticiler: {', '.join(summary['manufacturers'])}\n"
        f"Exact metadata: trim={exact_counts.get('trim_code', 0)}, "
        f"set-pressure={exact_counts.get('set_pressure_range', 0)}, "
        f"stamp={exact_counts.get('code_stamp', 0)}, "
        f"materials={exact_counts.get('body_material', 0)}/{exact_counts.get('trim_material', 0)}"
    )
