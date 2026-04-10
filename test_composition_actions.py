import os
import sys
import tkinter as tk

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from composition_actions import add_selected_gas, clear_composition, filter_gas_listbox, render_composition_text


def test_filter_gas_listbox_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        listbox = tk.Listbox(root)
        listbox.pack()
        filter_gas_listbox(listbox, ["Methane", "Ethane", "Nitrogen"], "eth")
        assert listbox.size() == 2
        assert listbox.get(0) == "Methane"
        assert listbox.get(1) == "Ethane"
    finally:
        root.destroy()


def test_add_selected_gas_and_clear():
    root = tk.Tk()
    root.withdraw()
    try:
        composition = {}
        listbox = tk.Listbox(root)
        listbox.pack()
        for gas in ["Methane", "Ethane"]:
            listbox.insert(tk.END, gas)
        listbox.selection_set(0)

        entry = tk.Entry(root)
        entry.pack()
        entry.insert(0, "95")

        text = tk.Text(root)
        text.pack()
        warnings = []

        added = add_selected_gas(
            composition,
            listbox,
            entry,
            text,
            showwarning_fn=lambda title, msg: warnings.append((title, msg)),
        )
        assert added is True
        assert composition["Methane"] == 95.0
        assert "Methane: 95.00%" in text.get("1.0", tk.END)
        assert not warnings

        clear_composition(composition, text)
        assert composition == {}
        assert text.get("1.0", tk.END).strip() == ""
    finally:
        root.destroy()


def test_render_composition_text_warning():
    root = tk.Tk()
    root.withdraw()
    try:
        text = tk.Text(root)
        text.pack()
        render_composition_text(text, {"Methane": 90.0, "Ethane": 5.0})
        content = text.get("1.0", tk.END)
        assert "TOPLAM: 95.00%" in content
        assert "Normallesecek" in content
    finally:
        root.destroy()


def test_add_selected_gas_overwrite_warning():
    root = tk.Tk()
    root.withdraw()
    try:
        composition = {"Methane": 80.0}
        listbox = tk.Listbox(root)
        listbox.pack()
        listbox.insert(tk.END, "Methane")
        listbox.selection_set(0)

        entry = tk.Entry(root)
        entry.pack()
        entry.insert(0, "95")

        text = tk.Text(root)
        text.pack()
        warnings = []

        added = add_selected_gas(
            composition,
            listbox,
            entry,
            text,
            showwarning_fn=lambda title, msg: warnings.append((title, msg)),
        )

        assert added is True
        assert composition["Methane"] == 95.0
        assert warnings
        assert "zaten listede mevcut" in warnings[0][1]
    finally:
        root.destroy()


if __name__ == "__main__":
    test_filter_gas_listbox_smoke()
    test_add_selected_gas_and_clear()
    test_render_composition_text_warning()
    test_add_selected_gas_overwrite_warning()
    print("TEST COMPLETED")
