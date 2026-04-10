import os
import sys
import tkinter as tk
from tkinter import ttk

from matplotlib.figure import Figure

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from ui_display_actions import (
    draw_figure_on_tab,
    set_text_widget_content,
    show_methodology_dialog,
    update_progress_widgets,
)


class DummyCanvas:
    def __init__(self):
        self.draw_calls = 0

    def draw(self):
        self.draw_calls += 1


def test_set_text_widget_content_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        widget = tk.Text(root)
        widget.pack()
        widget.config(state=tk.DISABLED)
        set_text_widget_content(widget, "hello")
        assert widget.get("1.0", tk.END).strip() == "hello"
        assert str(widget.cget("state")) == tk.DISABLED
    finally:
        root.destroy()


def test_set_text_widget_content_copyable_readonly():
    root = tk.Tk()
    root.withdraw()
    try:
        widget = tk.Text(root)
        widget.pack()
        widget.copyable_readonly = True
        set_text_widget_content(widget, "hello")
        assert widget.get("1.0", tk.END).strip() == "hello"
        assert str(widget.cget("state")) == tk.NORMAL
    finally:
        root.destroy()


def test_update_progress_widgets_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        label = ttk.Label(root, text="")
        progress = ttk.Progressbar(root, orient="horizontal", mode="determinate")
        update_progress_widgets(progress, label, 25, 100, "working")
        assert int(float(progress["value"])) == 25
        assert label["text"] == "working"
    finally:
        root.destroy()


def test_draw_figure_on_tab_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        notebook = ttk.Notebook(root)
        notebook.pack()
        tab1 = ttk.Frame(notebook)
        tab2 = ttk.Frame(notebook)
        notebook.add(tab1, text="A")
        notebook.add(tab2, text="B")
        fig = Figure(figsize=(4, 3))
        canvas = DummyCanvas()
        draw_figure_on_tab(fig, canvas, notebook, tab2)
        assert canvas.draw_calls == 1
        assert notebook.select() == str(tab2)
    finally:
        root.destroy()


def test_show_methodology_dialog_smoke():
    root = tk.Tk()
    root.withdraw()
    try:
        win = show_methodology_dialog(root, "example content")
        descendants = []
        for child in win.winfo_children():
            descendants.append(child)
            descendants.extend(child.winfo_children())
        texts = [child for child in descendants if isinstance(child, tk.Text)]
        assert texts
        assert "example content" in texts[0].get("1.0", tk.END)
        win.destroy()
    finally:
        root.destroy()


if __name__ == "__main__":
    test_set_text_widget_content_smoke()
    test_set_text_widget_content_copyable_readonly()
    test_update_progress_widgets_smoke()
    test_draw_figure_on_tab_smoke()
    test_show_methodology_dialog_smoke()
    print("TEST COMPLETED")
