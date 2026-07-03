from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui_mode_logic import (
    FIELD_BACKPRESSURE,
    FIELD_BACKPRESSURE_KB,
    FIELD_INNER_DIAMETER,
    FIELD_LENGTH,
    FIELD_MAWP,
    FIELD_OVERPRESSURE,
    FIELD_PSV_KD,
    FIELD_REQUIRED_FLOW,
    FIELD_START_PRESSURE,
    FIELD_START_TEMPERATURE,
    FIELD_TARGET_PRESSURE,
    FIELD_TARGET_TIME,
    FIELD_THICKNESS,
    FIELD_TOTAL_VOLUME,
    FIELD_VALVE_CD,
    FIELD_VALVE_COUNT,
)

FIELD_HELP_TEXT: dict[str, str] = {
    FIELD_INNER_DIAMETER: (
        "Boru hatti veya tankin ic capi.\n"
        "Geometrik hesaplama (hacim, yuzey alani) icin kullanilir.\n"
        "Toplam Hacim dogrudan girilirse bu alan opsiyoneldir."
    ),
    FIELD_LENGTH: (
        "Boru hatti veya tankin uzunlugu.\n"
        "Hacim ve isi transfer alani hesabi icin gereklidir."
    ),
    FIELD_THICKNESS: (
        "Boru / vessel cidar kalinligi.\n"
        "Celik kutlesi ve isi transferi hesaplamasinda kullanilir."
    ),
    FIELD_TOTAL_VOLUME: (
        "Sistemin toplam ic hacmi.\n"
        "Geometrik olculer (cap, uzunluk) yerine dogrudan girilebilir.\n"
        "⚠ Bu durumda isi transferi devre disi kalir."
    ),
    FIELD_START_PRESSURE: (
        "Blowdown baslangicindaki sistem basinci.\n"
        "Gauge (barg / psig) veya mutlak (bara / psia) birim secilebilir.\n"
        "Program otomatik olarak Pa'a cevirir."
    ),
    FIELD_START_TEMPERATURE: (
        "Blowdown baslangicindaki akiskan sicakligi.\n"
        "Gercek gaz ozellikleri (k, Z, yogunluk) bu sicaklikta hesaplanir.\n"
        "Gecerli aralik: 50 K ... 1500 K"
    ),
    FIELD_TARGET_PRESSURE: (
        "Ulasilmak istenen hedef basinc.\n"
        "API 521 fire case aktifse bu alan otomatik hesaplanir:\n"
        "  P_hedef = P_atm + 0.5 * (MAWP - P_atm)\n"
        "Hedef basinc, baslangic basincindan kucuk olmalidir."
    ),
    FIELD_TARGET_TIME: (
        "Sistemin hedef basinca ulasmasi istenen maksimum sure (saniye).\n"
        "API 521 fire case: tipik 900 s (15 dakika).\n"
        "Fire case aktifse otomatik atanir."
    ),
    FIELD_VALVE_COUNT: (
        "Paralel calisacak tahliye vanasi sayisi.\n"
        "Gerekli toplam alan vana sayisina bolunerek\n"
        "vana basina alan hesaplanir. En az 1 olmalidir."
    ),
    FIELD_VALVE_CD: (
        "Blowdown desarj katsayisi (Cd, 0...1 arasi).\n"
        "Tipik degerler:\n"
        "  0.975 - Tam acik kuresel vana (API 6D)\n"
        "  0.62  - Keskin kenarli orifis"
    ),
    FIELD_PSV_KD: (
        "PSV sertifikali desarj katsayisi (Kd).\n"
        "API 520 tipik degerler:\n"
        "  0.975 - Gas / Vapor servisi\n"
        "  0.975 - Steam servisi\n"
        "  0.650 - Liquid servisi"
    ),
    FIELD_BACKPRESSURE: (
        "Vana cikisindaki karsi basinc.\n"
        "Atmosfere acik tahliye: 0 barg.\n"
        "Flare / header sistemlerinde ayrica hesaplanmalidir."
    ),
    FIELD_BACKPRESSURE_KB: (
        "Karsi basinc duzeltme faktoru (Kb).\n"
        "Kritik akista: 1.0\n"
        "Subkritik akista: < 1.0 (API 520 Figur 30'dan)\n"
        "Bilinmiyorsa 1.0 birakilabilir (konservatif)."
    ),
    FIELD_MAWP: (
        "Maksimum Izin Verilen Calisma Basinci / Tasarim Basinci.\n"
        "Fire case hedef basinci bu degerden turetilir.\n"
        "API 521: P_hedef = P_atm + 0.5 * (MAWP - P_atm)"
    ),
    FIELD_OVERPRESSURE: (
        "PSV icin izin verilen asiri basinc yuzdesi (% olarak).\n"
        "API 520-1 tipik degerler:\n"
        "  %10 - Normal senaryo\n"
        "  %21 - Yangin senaryosu"
    ),
    FIELD_REQUIRED_FLOW: (
        "Tahliye edilmesi gereken kutlesel / hacimsel debi.\n"
        "PSV boyutlandirmasi icin zorunlu giris.\n"
        "Desteklenen birimler: kg/h, lb/h, Nm3/h, SCFM, MMSCFD"
    ),
}

TOOLTIP_DELAY_MS = 450


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self._job = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Button-1>", self._show_now, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._job = self.widget.after(TOOLTIP_DELAY_MS, self._show)

    def _show_now(self, _event=None):
        self._cancel()
        self._show()

    def _cancel(self):
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None

    def _show(self):
        if self.tip_window is not None:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        self.tip_window.attributes("-topmost", True)
        frame = ttk.Frame(self.tip_window, relief="solid", borderwidth=1, padding=8)
        frame.pack()
        label = ttk.Label(frame, text=self.text, wraplength=340, justify="left")
        label.pack()
        try:
            style = ttk.Style()
            style.configure("Tooltip.TLabel", background="#fffde7", foreground="#2c3e50")
            style.configure("Tooltip.TFrame", background="#fffde7")
            frame.configure(style="Tooltip.TFrame")
            label.configure(style="Tooltip.TLabel")
        except Exception:
            pass

    def _hide(self, _event=None):
        self._cancel()
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None
