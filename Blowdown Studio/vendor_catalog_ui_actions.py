from __future__ import annotations


def import_vendor_catalog_dialog(
    *,
    askopenfilename_fn,
    load_with_summary_fn,
    format_loaded_message_fn,
    showinfo_fn,
    showerror_fn,
):
    file_path = askopenfilename_fn(
        title="Vendor Katalogu Sec",
        filetypes=[("Catalog Files", "*.json *.csv"), ("JSON Files", "*.json"), ("CSV Files", "*.csv")],
    )
    if not file_path:
        return None
    try:
        _, summary = load_with_summary_fn(file_path)
        showinfo_fn("Vendor Catalog", format_loaded_message_fn(summary))
        return file_path
    except Exception as exc:
        showerror_fn("Vendor Catalog", f"Katalog yuklenemedi: {exc}")
        return None


def reset_vendor_catalog_dialog(*, showinfo_fn):
    showinfo_fn("Vendor Catalog", "Built-in varsayilan vendor katalogu aktif.")
    return None


def show_vendor_catalog_summary_dialog(
    vendor_catalog_path,
    *,
    get_summary_fn,
    format_summary_message_fn,
    showinfo_fn,
    showerror_fn,
):
    try:
        summary = get_summary_fn(vendor_catalog_path)
    except Exception as exc:
        showerror_fn("Vendor Catalog", f"Katalog okunamadi: {exc}")
        return None
    message = format_summary_message_fn(summary)
    showinfo_fn("Vendor Catalog Summary", message)
    return summary
