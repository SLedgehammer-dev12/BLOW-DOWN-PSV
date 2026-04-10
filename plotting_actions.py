from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from api521_discharge_piping import calculate_discharge_piping_loss
from constants import P_ATM
from native_blowdown_engine import NATIVE_ENGINE_NAME, calculate_reaction_force


def draw_graph_placeholder(fig, mode_text: str) -> None:
    fig.clf()
    ax = fig.add_subplot(1, 1, 1)
    label = (
        "PSV ön boyutlandırma tamamlandığında grafikler burada görünecek."
        if "PSV" in mode_text
        else "Blowdown simülasyonu tamamlandığında grafikler burada görünecek."
    )
    ax.text(0.5, 0.5, label, ha="center", va="center", transform=ax.transAxes, fontsize=12)
    ax.set_axis_off()
    fig.tight_layout()


def render_blowdown_plots(fig, sim_df, inputs, valve=None) -> None:
    fig.clf()
    fig.set_size_inches(14, 10, forward=False)
    axes = fig.subplots(4, 3)
    engine_name = sim_df.attrs.get("engine", NATIVE_ENGINE_NAME)
    used_axes = {(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)}

    axes[0, 0].plot(sim_df["t"], sim_df["p_sys"] / 1e5, color="blue")
    axes[0, 0].set_ylabel("Basınç (bara)")
    axes[0, 0].set_title(f"{engine_name} - Kap Basıncı Düşümü")
    axes[0, 0].grid(True)

    axes[0, 1].plot(sim_df["t"], sim_df["mdot_kg_s"] * 3600.0, color="purple")
    axes[0, 1].set_ylabel("Kütlesel Tahliye (kg/h)")
    axes[0, 1].set_title("Vana Eşzamanlı Debisi")
    axes[0, 1].grid(True)

    axes[1, 0].plot(sim_df["t"], sim_df["m_sys"], color="red")
    axes[1, 0].set_ylabel("Kalan Kütle (kg)")
    axes[1, 0].set_title("Sistem Kütle Azalışı")
    axes[1, 0].grid(True)

    rho_safe = np.maximum(np.asarray(sim_df["rho_g"], dtype=float), 1e-12)
    volumetric_flow_m3_h = (np.asarray(sim_df["mdot_kg_s"], dtype=float) * 3600.0) / rho_safe
    axes[1, 1].plot(sim_df["t"], volumetric_flow_m3_h, color="green")
    axes[1, 1].set_ylabel("Hacimsel Tahliye (m3/h)")
    axes[1, 1].set_title("Volümetrik Çıkış Miktarı")
    axes[1, 1].grid(True)

    axes[2, 0].plot(sim_df["t"], sim_df["T_sys"] - 273.15, label="Gaz", color="orange")
    axes[2, 0].plot(sim_df["t"], sim_df["T_wall"] - 273.15, label="Metal", color="black", alpha=0.7)
    axes[2, 0].set_ylabel("Sıcaklık (C)")
    axes[2, 0].set_xlabel("Zaman (s)")
    axes[2, 0].set_title("Sıcaklık Dalgalanmaları")
    axes[2, 0].legend()
    axes[2, 0].grid(True)

    axes[2, 1].plot(sim_df["t"], sim_df["h_in"], color="brown")
    axes[2, 1].set_ylabel("Konveksiyon (W/m2K)")
    axes[2, 1].set_xlabel("Zaman (s)")
    axes[2, 1].set_title("Ic Isi Transfer Katsayisi")
    axes[2, 1].grid(True)

    segmented_axis = None
    if {"p_upstream", "p_terminal", "p_avg"}.issubset(sim_df.columns):
        segmented_axis = (0, 2) if not inputs.get("fire_case", False) else (3, 0)
        used_axes.add(segmented_axis)
        ax_seg = axes[segmented_axis]
        ax_seg.plot(sim_df["t"], sim_df["p_upstream"] / 1e5, label="Upstream", color="navy")
        ax_seg.plot(sim_df["t"], sim_df["p_avg"] / 1e5, label="Average", color="teal")
        ax_seg.plot(sim_df["t"], sim_df["p_terminal"] / 1e5, label="Terminal", color="darkorange")
        ax_seg.set_ylabel("Basınç (bara)")
        ax_seg.set_xlabel("Zaman (s)")
        ax_seg.set_title("Segmentli Pipeline Basınç Profili")
        ax_seg.legend()
        ax_seg.grid(True)

    if "quality" in sim_df.columns:
        quality_axis = (3, 0) if segmented_axis != (3, 0) else (0, 2)
        used_axes.add(quality_axis)
        axes[quality_axis].plot(sim_df["t"], sim_df["quality"], color="teal", linewidth=2)
        axes[quality_axis].set_ylabel("Vapor Quality (x)")
        axes[quality_axis].set_xlabel("Zaman (s)")
        axes[quality_axis].set_title("Iki Faz Vapor Kalitesi (Homogeneous Model)")
        axes[quality_axis].grid(True)
        axes[quality_axis].axhline(0.1, color="gray", linestyle="--", alpha=0.5, label="Initial Guess")
        axes[quality_axis].legend()

    if ("discharge_piping" in inputs or "discharge_K" in inputs) and "pipe_diameter_mm" in inputs:
        used_axes.add((3, 1))
        pipe_d_mm = inputs.get("pipe_diameter_mm", 50.0)
        pipe_length_m = inputs.get("pipe_length_m", 5.0)
        elbow_count = inputs.get("elbow_count", 2)
        tee_count = inputs.get("tee_count", 0)
        globe_valve_count = inputs.get("globe_valve_count", 0)
        check_valve_count = inputs.get("check_valve_count", 0)
        butterfly_valve_count = inputs.get("butterfly_valve_count", 0)

        piping_loss = inputs.get("discharge_piping")
        if piping_loss is None:
            piping_loss = calculate_discharge_piping_loss(
                pipe_length_m=pipe_length_m,
                pipe_diameter_mm=pipe_d_mm,
                elbow_count=elbow_count,
                tee_count=tee_count,
                globe_valve_count=globe_valve_count,
                check_valve_count=check_valve_count,
                butterfly_valve_count=butterfly_valve_count,
            )

        fitting_components = [
            piping_loss["pipe_friction_loss"],
            0.30 * elbow_count,
            0.20 * tee_count,
            10.0 * globe_valve_count,
            5.0 * check_valve_count,
            2.0 * butterfly_valve_count,
        ]
        axes[3, 1].barh(
            ["Pipe Friction", "Elbows", "Tees", "Globe Valves", "Check Valves", "Butterfly"],
            fitting_components,
            color=["steelblue", "orange", "lightcoral", "green", "purple", "slategray"],
        )
        axes[3, 1].set_xlabel("K Faktörü")
        axes[3, 1].set_title("API 521 Discharge Piping Loss (K Faktörü)")
        axes[3, 1].grid(axis="y")
        axes[3, 1].text(0.02, 1.02, f'Total K: {piping_loss["total_K"]:.3f}', transform=axes[3, 1].transAxes, fontsize=9)
        axes[3, 1].text(
            0.02,
            0.98,
            f'Equivalent Length: {piping_loss["equivalent_length_m"]:.1f} m',
            transform=axes[3, 1].transAxes,
            fontsize=9,
        )

    if "acoustic_velocity" in inputs or "mach_number" in sim_df.columns:
        used_axes.add((3, 2))
        acoustic_velocity = inputs.get("acoustic_velocity", 400.0)
        if "mach_number" in sim_df.columns:
            axes[3, 2].plot(sim_df["t"], sim_df["mach_number"], color="red", linewidth=2, label="Mach")
            axes[3, 2].axhline(0.3, color="orange", linestyle="--", label="Screening (0.3)")
            axes[3, 2].axhline(0.5, color="gold", linestyle="--", label="Moderate (0.5)")
            axes[3, 2].axhline(0.7, color="darkred", linestyle="--", label="High (0.7)")
            axes[3, 2].set_ylabel("Mach Number")
            axes[3, 2].set_xlabel("Zaman (s)")
            axes[3, 2].set_title("Acoustic Screening (Mach Number)")
            axes[3, 2].legend()
            axes[3, 2].grid(True)
        else:
            discharge_velocity = inputs.get("discharge_velocity", 100.0)
            if discharge_velocity and acoustic_velocity:
                mach = discharge_velocity / acoustic_velocity
                axes[3, 2].plot(sim_df["t"], [mach] * len(sim_df), color="red", linewidth=2)
                axes[3, 2].set_ylabel("Mach Number")
                axes[3, 2].set_xlabel("Zaman (s)")
                axes[3, 2].set_title(f"Acoustic Screening (Mach = {mach:.3f})")
                axes[3, 2].grid(True)
                axes[3, 2].text(
                    0.5,
                    0.5,
                    f"Mach: {mach:.3f}\nAcoustic Velocity: {acoustic_velocity:.1f} m/s",
                    ha="center",
                    va="center",
                    transform=axes[3, 2].transAxes,
                    fontsize=9,
                )

    if inputs.get("fire_case", False):
        used_axes.add((0, 2))
        ax_fire = axes[0, 2]
        ax_fire.set_title("API 521 Fire Case Screening")
        ax_fire.set_axis_off()
        fire_lines = [
            f'Design Pressure : {inputs.get("design_pressure_pa", 0.0) / 1e5:.3f} bara',
            f'Target Pressure : {inputs.get("fire_case_target_pressure_pa", 0.0) / 1e5:.3f} bara',
            f'Target Time     : {inputs.get("fire_case_target_time_s", 0.0):.0f} s',
            f'Scenario        : {inputs.get("fire_case_scenario", "N/A")}',
            f'Env. Factor F   : {inputs.get("fire_environment_factor", 1.0):.3f}',
        ]
        if inputs.get("fire_wetted_area_m2") is not None:
            fire_lines.append(f'Wetted Area     : {inputs["fire_wetted_area_m2"]:.2f} m2')
        if inputs.get("fire_heat_input_w") is not None:
            fire_lines.append(f'Heat Input      : {inputs["fire_heat_input_w"] / 1000.0:,.1f} kW')
        ax_fire.text(0.02, 0.98, "\n".join(fire_lines), ha="left", va="top", transform=ax_fire.transAxes, fontsize=10, family="monospace")

    for i in range(4):
        for j in range(3):
            if (i, j) not in used_axes:
                axes[i, j].set_visible(False)

    fig.tight_layout()


def render_psv_plots(
    fig,
    sizing,
    inputs,
    selected_valve,
    valve_data,
    vendor_selection,
    vendor_evaluation,
    force_n_design,
    valve_count,
    valve_type_selection: str,
) -> None:
    del selected_valve

    fig.clf()
    axes = fig.subplots(2, 2)
    service_type = inputs.get("psv_service_type", "Gas/Vapor")
    required_area_mm2 = sizing.A_req_mm2 / max(valve_count, 1)
    mass_flow_kg_h = inputs.get("W_req_kg_h", getattr(sizing, "W_req_kg_h", 0.0))
    flow_per_valve_kg_s = (mass_flow_kg_h / 3600.0) / max(valve_count, 1) if mass_flow_kg_h else 0.0

    ax1 = axes[0, 0]
    if "API 526" in valve_type_selection:
        letters = [o.letter for o in valve_data]
        areas = [o.area_mm2 for o in valve_data]
        colors_b = []
        selected_found = False
        for item in valve_data:
            if not selected_found and item.area_mm2 >= required_area_mm2:
                colors_b.append("tomato")
                selected_found = True
            elif item.area_mm2 >= required_area_mm2:
                colors_b.append("lightcoral")
            else:
                colors_b.append("steelblue")
        ax1.bar(letters, areas, color=colors_b, edgecolor="black", linewidth=0.5)
        ax1.axhline(required_area_mm2, color="purple", linestyle="--", linewidth=1.5, label=f"Gerekli: {required_area_mm2:.0f} mm2")
        ax1.set_xlabel("API 526 Orifis")
        ax1.set_ylabel("Efektif Alan (mm2)")
        ax1.set_title("Standart Orifis Karşılaştırması")
        ax1.legend()
        ax1.grid(axis="y")
    else:
        ax1.text(0.5, 0.5, "API 526 grafigi bu secim icin uygulanmadi.", ha="center", va="center", transform=ax1.transAxes)
        ax1.set_axis_off()

    ax2 = axes[0, 1]
    if service_type == "Gas/Vapor" and vendor_evaluation and vendor_evaluation.evaluated:
        display_items = vendor_evaluation.evaluated[: min(8, len(vendor_evaluation.evaluated))]
        labels = [item.model.display_size for item in display_items]
        margins = [item.certified_capacity_margin_pct for item in display_items]
        colors_b = ["seagreen" if item.meets_required_capacity and item.meets_required_effective_area else "darkorange" for item in display_items]
        ax2.bar(range(len(display_items)), margins, color=colors_b)
        ax2.axhline(0.0, color="black", linewidth=1.0)
        ax2.set_xticks(range(len(display_items)))
        ax2.set_xticklabels(labels, rotation=35, ha="right")
        ax2.set_ylabel("Capacity Margin (%)")
        ax2.set_title("Vendor Certified Capacity Screening")
        ax2.grid(axis="y")
    else:
        msg = "Vendor screening verisi bulunamadi." if service_type == "Gas/Vapor" else "Vendor screening yalniz Gas/Vapor icin aktif."
        ax2.text(0.5, 0.5, msg, ha="center", va="center", transform=ax2.transAxes)
        ax2.set_axis_off()

    ax3 = axes[1, 0]
    if valve_data and service_type in {"Gas/Vapor", "Steam"} and force_n_design is not None and getattr(sizing, "k_real", None) and getattr(sizing, "MW_kg_kmol", None):
        x_labels = [item.letter if hasattr(item, "letter") else item.size_in for item in valve_data]
        forces = [
            calculate_reaction_force(
                flow_per_valve_kg_s,
                inputs["relieving_temperature_k"],
                sizing.relieving_pressure_pa,
                max(item.area_mm2, 1e-9) / 1e6,
                float(sizing.k_real),
                float(sizing.MW_kg_kmol),
                p_exit_pa=getattr(sizing, "backpressure_pa", P_ATM),
            )
            / 1000.0
            for item in valve_data
        ]
        ax3.plot(x_labels, forces, color="darkorange", marker="o", linewidth=2)
        ax3.axhline(force_n_design / 1000.0, color="red", linestyle="--", label="Secilen vana kuvveti")
        ax3.set_ylabel("Reaksiyon Kuvveti (kN)")
        ax3.set_title("Vana Boyutuna Gore Reaksiyon Kuvveti")
        ax3.legend()
        ax3.grid(True)
    else:
        msg = "Liquid service icin reaksiyon grafigi aktif degil." if service_type == "Liquid" else "Mekanik screening verisi yok."
        ax3.text(0.5, 0.5, msg, ha="center", va="center", transform=ax3.transAxes)
        ax3.set_axis_off()

    ax4 = axes[1, 1]
    if service_type == "Liquid":
        actual_bp = sizing.backpressure_pct_of_set
        ax4.axvline(actual_bp, color="red", linestyle="--", label=f"Mevcut BP: {actual_bp:.1f}%")
        ax4.bar(["Kw"], [getattr(sizing, "Kw_used", 1.0)], color="seagreen")
        ax4.set_ylabel("Kw")
        ax4.set_ylim(0.0, 1.1)
        ax4.set_title("Liquid Backpressure Screening")
        ax4.legend()
        ax4.grid(True)
    else:
        bp_pct_range = np.linspace(0, 50, 100)
        kb_conv = np.where(bp_pct_range <= 10, 1.0, np.maximum(0.0, 1.0 - (bp_pct_range - 10) / 40.0))
        kb_bbell = np.where(bp_pct_range <= 30, 1.0, np.maximum(0.0, 1.0 - (bp_pct_range - 30) / 20.0))
        actual_bp = sizing.backpressure_pct_of_set
        ax4.plot(bp_pct_range, kb_conv, color="steelblue", linewidth=2, label="Conventional")
        ax4.plot(bp_pct_range, kb_bbell, color="seagreen", linewidth=2, label="Balanced Bellows")
        ax4.axvline(actual_bp, color="red", linestyle="--", label=f"Mevcut BP: {actual_bp:.1f}%")
        if vendor_selection is not None:
            ax4.scatter([actual_bp], [vendor_selection.kb_used], color="black", zorder=5, label=f"Secilen Kb: {vendor_selection.kb_used:.3f}")
        ax4.set_xlabel("Karşı Basınç / Set (%)")
        ax4.set_ylabel("Kb")
        ax4.set_ylim(0.0, 1.1)
        ax4.set_title("Backpressure Screening")
        ax4.legend()
        ax4.grid(True)

    fig.tight_layout()


def simple_psv_plot_inputs(**overrides):
    """
    Small helper for tests to build a stable default PSV plotting payload.
    """
    payload = {
        "psv_service_type": "Gas/Vapor",
        "W_req_kg_h": 10000.0,
        "relieving_temperature_k": 300.0,
    }
    payload.update(overrides)
    return payload


def simple_psv_sizing(**overrides):
    """
    Small helper for tests to build a stable sizing-like object.
    """
    payload = {
        "A_req_mm2": 126.5,
        "backpressure_pct_of_set": 5.0,
        "relieving_pressure_pa": 12e5,
        "k_real": 1.25,
        "MW_kg_kmol": 18.0,
        "Kw_used": 0.95,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)
