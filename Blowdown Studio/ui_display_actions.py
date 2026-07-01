from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext


def set_text_widget_content(text_widget, text: str, *, readonly: bool = True) -> None:
    use_copyable_readonly = readonly and bool(getattr(text_widget, "copyable_readonly", False))
    if readonly:
        text_widget.config(state=tk.NORMAL)
    text_widget.delete("1.0", tk.END)
    text_widget.insert(tk.END, text)
    if readonly and not use_copyable_readonly:
        text_widget.config(state=tk.DISABLED)


def update_progress_widgets(progress_widget, label_widget, current, target, text: str = "") -> None:
    if target > 0:
        progress_widget["value"] = (current / target) * 100
    if text:
        label_widget["text"] = text


def draw_figure_on_tab(fig, canvas, notebook, tab) -> None:
    canvas.draw()
    notebook.select(tab)


def show_methodology_dialog(parent, content: str, *, title: str = "Modelleme ve Hesaplama Metodolojisi", geometry: str = "700x600"):
    help_win = tk.Toplevel(parent)
    help_win.title(title)
    help_win.geometry(geometry)

    txt = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=("Arial", 10))
    txt.pack(expand=True, fill="both")
    txt.insert(tk.END, content)
    txt.config(state=tk.DISABLED)
    return help_win
