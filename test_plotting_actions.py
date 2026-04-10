import os
import sys
from collections import namedtuple
from types import SimpleNamespace

import pandas as pd
from matplotlib.figure import Figure

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from plotting_actions import (
    draw_graph_placeholder,
    render_blowdown_plots,
    render_psv_plots,
    simple_psv_plot_inputs,
    simple_psv_sizing,
)


Valve = namedtuple("Valve", ["letter", "area_mm2", "size_in"])


def test_draw_graph_placeholder_smoke():
    fig = Figure(figsize=(6, 4))
    draw_graph_placeholder(fig, "Blowdown")
    assert len(fig.axes) == 1
    assert fig.axes[0].axison is False


def test_render_blowdown_plots_smoke():
    fig = Figure(figsize=(8, 6))
    sim_df = pd.DataFrame(
        [
            {
                "t": 0.0,
                "p_sys": 12e5,
                "mdot_kg_s": 1.2,
                "T_sys": 300.0,
                "T_wall": 302.0,
                "h_in": 10.0,
                "rho_g": 8.0,
                "m_sys": 100.0,
                "mach_number": 0.35,
            },
            {
                "t": 10.0,
                "p_sys": 5e5,
                "mdot_kg_s": 0.6,
                "T_sys": 290.0,
                "T_wall": 296.0,
                "h_in": 8.0,
                "rho_g": 4.0,
                "m_sys": 80.0,
                "mach_number": 0.28,
            },
        ]
    )
    sim_df.attrs["engine"] = "Yerel Çözücü"
    inputs = {
        "pipe_diameter_mm": 50.0,
        "pipe_length_m": 5.0,
        "elbow_count": 2,
        "discharge_piping": {"pipe_friction_loss": 1.1, "total_K": 2.5, "equivalent_length_m": 7.3},
        "acoustic_velocity": 420.0,
    }

    render_blowdown_plots(fig, sim_df, inputs)

    titles = {ax.get_title() for ax in fig.axes if ax.get_visible()}
    assert "Yerel Çözücü - Kap Basıncı Düşümü" in titles
    assert "API 521 Discharge Piping Loss (K Faktörü)" in titles
    assert "Acoustic Screening (Mach Number)" in titles


def test_render_psv_plots_smoke():
    fig = Figure(figsize=(8, 6))
    sizing = simple_psv_sizing()
    inputs = simple_psv_plot_inputs()
    valve_data = [
        Valve("D", 71.0, '1"'),
        Valve("E", 126.5, '1"'),
        Valve("F", 198.1, '1.5"'),
    ]
    vendor_item = SimpleNamespace(
        model=SimpleNamespace(display_size="E"),
        certified_capacity_margin_pct=12.0,
        meets_required_capacity=True,
        meets_required_effective_area=True,
    )
    vendor_evaluation = SimpleNamespace(evaluated=[vendor_item])
    vendor_selection = SimpleNamespace(kb_used=1.0)

    render_psv_plots(
        fig,
        sizing,
        inputs,
        selected_valve=valve_data[1],
        valve_data=valve_data,
        vendor_selection=vendor_selection,
        vendor_evaluation=vendor_evaluation,
        force_n_design=12000.0,
        valve_count=1,
        valve_type_selection="API 526 (PSV/PRV)",
    )

    titles = {ax.get_title() for ax in fig.axes}
    assert "Standart Orifis Karşılaştırması" in titles
    assert "Vendor Certified Capacity Screening" in titles
    assert "Backpressure Screening" in titles


def test_render_blowdown_plots_repeated_smoke():
    fig = Figure(figsize=(8, 6))
    sim_df = pd.DataFrame(
        [
            {
                "t": 0.0,
                "p_sys": 12e5,
                "mdot_kg_s": 1.2,
                "T_sys": 300.0,
                "T_wall": 302.0,
                "h_in": 10.0,
                "rho_g": 8.0,
                "m_sys": 100.0,
                "mach_number": 0.35,
            },
            {
                "t": 10.0,
                "p_sys": 5e5,
                "mdot_kg_s": 0.6,
                "T_sys": 290.0,
                "T_wall": 296.0,
                "h_in": 8.0,
                "rho_g": 4.0,
                "m_sys": 80.0,
                "mach_number": 0.28,
            },
        ]
    )
    sim_df.attrs["engine"] = "Yerel Çözücü"
    inputs = {
        "pipe_diameter_mm": 50.0,
        "pipe_length_m": 5.0,
        "elbow_count": 2,
        "discharge_piping": {"pipe_friction_loss": 1.1, "total_K": 2.5, "equivalent_length_m": 7.3},
        "acoustic_velocity": 420.0,
    }

    for _ in range(20):
        render_blowdown_plots(fig, sim_df, inputs)
        assert len(fig.axes) == 12

    visible_titles = {ax.get_title() for ax in fig.axes if ax.get_visible()}
    assert "Yerel Çözücü - Kap Basıncı Düşümü" in visible_titles


if __name__ == "__main__":
    test_draw_graph_placeholder_smoke()
    test_render_blowdown_plots_smoke()
    test_render_psv_plots_smoke()
    test_render_blowdown_plots_repeated_smoke()
    print("TEST COMPLETED")
