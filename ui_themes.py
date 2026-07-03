from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import platform

THEME_PERFORMANCE = "Performans (Varsayilan)"
THEME_MODERN_LIGHT = "Modern Acik"
THEME_MODERN_DARK = "Modern Koyu"

THEME_LIST = [THEME_MODERN_LIGHT, THEME_MODERN_DARK, THEME_PERFORMANCE]

LIGHT_PALETTE = {
    "bg": "#f5f6fa",
    "section_bg": "#ffffff",
    "accent": "#3498db",
    "text": "#2c3e50",
    "border": "#dcdde1",
    "heading": "#1a5276",
    "canvas_bg": "#f8f9fa",
    "results_bg": "#ffffff",
    "section_label_fg": "#1a5276",
    "help_fg": "#7f8c8d",
    "titlebar_bg": "#ffffff",
}

DARK_PALETTE = {
    "bg": "#1a1a2e",
    "section_bg": "#16213e",
    "accent": "#0f3460",
    "text": "#e0e0e0",
    "border": "#2a2a4a",
    "heading": "#4facfe",
    "canvas_bg": "#1e1e32",
    "results_bg": "#16213e",
    "section_label_fg": "#4facfe",
    "help_fg": "#8a8aaa",
    "titlebar_bg": "#16213e",
}


def _get_system_font():
    system = platform.system()
    if system == "Windows":
        return "Segoe UI"
    elif system == "Darwin":
        return "SF Pro Text"
    else:
        return "Sans"


def apply_theme(app, theme_name: str):
    style = ttk.Style()

    if theme_name == THEME_PERFORMANCE:
        _reset_to_performance(app, style)
        return

    palette = LIGHT_PALETTE if theme_name == THEME_MODERN_LIGHT else DARK_PALETTE
    sys_font = _get_system_font()

    available = style.theme_names()
    if "clam" in available:
        style.theme_use("clam")
    else:
        style.theme_use(available[0])

    style.configure(".", background=palette["bg"], foreground=palette["text"], font=(sys_font, 10))
    style.configure("TLabel", background=palette["bg"], foreground=palette["text"])
    style.configure("TFrame", background=palette["bg"])
    style.configure("TLabelframe", background=palette["section_bg"], relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=palette["section_bg"], foreground=palette["section_label_fg"], font=(sys_font, 10, "bold"))
    style.configure("TButton", font=(sys_font, 10), padding=6)
    style.configure("TEntry", fieldbackground=palette["section_bg"], foreground=palette["text"])
    style.configure("TCombobox", fieldbackground=palette["section_bg"], foreground=palette["text"])
    style.configure("TCheckbutton", background=palette["bg"])
    style.configure("TProgressbar", troughcolor=palette["border"])
    style.configure("TSeparator", background=palette["border"])
    style.configure("Vertical.TScrollbar", background=palette["bg"], troughcolor=palette["border"])

    style.map("TButton", background=[("active", palette["accent"])])
    if palette == LIGHT_PALETTE:
        style.map("TButton", foreground=[("active", "#ffffff")])

    if theme_name == THEME_DARK:
        try:
            app.tk_setPalette(background=palette["bg"], foreground=palette["text"],
                              activeBackground=palette["accent"], activeForeground=palette["text"])
        except Exception:
            pass

    _apply_canvas_styles(app, palette, sys_font)
    _apply_text_widget_styles(app, palette)

    app.current_theme = theme_name


def _reset_to_performance(app, style):
    available = style.theme_names()
    default_theme = "aqua" if "aqua" in available else available[0]
    style.theme_use(default_theme)
    try:
        app.tk_setPalette(background="SystemButtonFace", foreground="SystemButtonText")
    except Exception:
        pass


def _apply_canvas_styles(app, palette, _font):
    if hasattr(app, "left_canvas") and app.left_canvas.winfo_exists():
        app.left_canvas.configure(background=palette["canvas_bg"])


def _apply_text_widget_styles(app, palette):
    if hasattr(app, "results_text") and app.results_text.winfo_exists():
        app.results_text.configure(bg=palette["results_bg"], fg=palette["text"])
    if hasattr(app, "comp_text") and app.comp_text.winfo_exists():
        app.comp_text.configure(bg=palette["results_bg"], fg=palette["text"])
    if hasattr(app, "log_text") and app.log_text.winfo_exists():
        app.log_text.configure(bg=palette["results_bg"], fg=palette["text"])
    if hasattr(app, "progress_label"):
        app.progress_label.configure(background=palette["bg"], foreground=palette["text"])
    if hasattr(app, "mode_help_label"):
        app.mode_help_label.configure(background=palette["bg"], foreground=palette["help_fg"])
    if hasattr(app, "api_results_text") and app.api_results_text.winfo_exists():
        app.api_results_text.configure(bg=palette["results_bg"], fg=palette["text"])
