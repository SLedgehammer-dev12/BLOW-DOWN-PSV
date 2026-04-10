from __future__ import annotations

import tkinter as tk


def filter_gas_listbox(gas_listbox, available_gases, search_term: str) -> None:
    gas_listbox.delete(0, tk.END)
    lowered = (search_term or "").lower()
    for gas in available_gases:
        if lowered in gas.lower():
            gas_listbox.insert(tk.END, gas)


def render_composition_text(comp_text, composition: dict[str, float]) -> None:
    comp_text.config(state=tk.NORMAL)
    comp_text.delete("1.0", tk.END)
    total = sum(composition.values())
    if total > 0:
        for gas, frac in composition.items():
            comp_text.insert(tk.END, f"{gas}: {frac:.2f}%\n")
        comp_text.insert(tk.END, f"----------\nTOPLAM: {total:.2f}%")
        if abs(total - 100.0) > 0.01:
            comp_text.insert(tk.END, " (Normallesecek)", "WARNING")
            comp_text.tag_config("WARNING", foreground="orange")
    comp_text.config(state=tk.DISABLED)


def add_selected_gas(composition: dict[str, float], gas_listbox, mole_entry, comp_text, *, showwarning_fn) -> bool:
    selected = gas_listbox.curselection()
    if not selected:
        return False

    gas = gas_listbox.get(selected[0])
    frac_str = mole_entry.get().strip()
    try:
        frac = float(frac_str)
        if frac <= 0:
            return False
        existing = gas in composition
        composition[gas] = frac
        if existing:
            showwarning_fn("Uyarı", f"{gas} zaten listede mevcut. Yeni değer ({frac:.1f}%) ile güncellendi.")
        render_composition_text(comp_text, composition)
        mole_entry.delete(0, tk.END)
        return True
    except ValueError:
        showwarning_fn("Geçersiz Giriş", "Lütfen geçerli bir mol yüzdesi girin.")
        return False


def clear_composition(composition: dict[str, float], comp_text) -> None:
    composition.clear()
    render_composition_text(comp_text, composition)
