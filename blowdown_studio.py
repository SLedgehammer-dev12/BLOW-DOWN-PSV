import numpy as np
import pandas as pd
import CoolProp.CoolProp as CP
import logging
from collections import namedtuple
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import math
import warnings
from ui_file_actions import (
    apply_settings_payload,
    build_settings_payload,
    export_blowdown_bundle_with_dialog,
    export_psv_bundle_with_dialog,
    read_settings_payload,
    show_blowdown_export_result,
    show_psv_export_result,
    write_settings_payload,
)
from ui_builders import (
    build_application_shell_ui,
    build_api2000_pane_ui,
    build_gas_settings_ui,
    build_left_pane_ui,
    build_main_settings_ui,
    build_menu_bar,
    build_right_pane_ui,
)
from composition_actions import add_selected_gas, clear_composition, filter_gas_listbox, render_composition_text
from execution_ui_actions import run_blowdown_ui_flow_with_feedback, run_psv_ui_flow_with_feedback
from input_collection_actions import collect_blowdown_inputs
from ui_display_actions import draw_figure_on_tab, set_text_widget_content, show_methodology_dialog, update_progress_widgets
from ui_mode_logic import build_mode_ui_state, build_psv_service_field_config
from ui_state_actions import apply_mode_change, configure_psv_service_fields, set_field_label, set_unit_options
from api2000_workflow import run_api2000_workflow
from api2000_ui_actions import run_api2000_ui_with_feedback
from api521_fire_case import build_pool_fire_case_screening
from blowdown_workflow import build_blowdown_report, run_blowdown_engine, select_standard_valve, size_blowdown_area
from blowdown_ui_actions import execute_blowdown_ui_flow
from blowdown_export_ui_actions import export_blowdown_report_with_feedback
from blowdown_reporting import export_blowdown_report_csv, export_blowdown_report_pdf
from constants import P_ATM, R_U, T_STD
from methodology_content import build_methodology_text
from native_blowdown_engine import (
    NATIVE_ENGINE_NAME,
    find_native_blowdown_area,
    run_native_blowdown_simulation,
)
from plotting_actions import draw_graph_placeholder, render_blowdown_plots, render_psv_plots
from psv_preliminary import (
    calculate_preliminary_gas_psv_area,
)
from psv_export_ui_actions import export_psv_report_with_feedback
from psv_reporting import export_psv_report_csv, export_psv_report_pdf
from psv_ui_actions import apply_psv_workflow_result, collect_psv_ui_payload
from psv_workflow import execute_psv_workflow
from run_control_actions import dispatch_run, start_blowdown_thread
from vendor_catalog_actions import (
    format_vendor_catalog_loaded_message,
    format_vendor_catalog_summary_message,
    get_active_vendor_catalog,
    get_active_vendor_catalog_summary,
    load_vendor_catalog_with_summary,
)
from vendor_catalog_ui_actions import (
    import_vendor_catalog_dialog,
    reset_vendor_catalog_dialog,
    show_vendor_catalog_summary_dialog,
)
from update_actions import (
    choose_update_download_path,
    default_update_download_path,
    fetch_latest_release,
    is_update_available,
)
from update_flow_actions import prompt_and_start_update_download, start_update_check_async
from update_ui_actions import prompt_update_download_path, start_update_download_async
from segmented_pipeline import (
    SEGMENTED_ENGINE_NAME,
)

# Constants and Data Structures
APP_NAME = "Blowdown Studio"
APP_VERSION = "v2.4.0"
TWO_PHASE_ENGINE_NAME = "Two-Phase Screening"

API526_Orifice = namedtuple('API526_Orifice', ['letter', 'area_in2', 'area_mm2', 'size_in', 'size_dn'])
# API 6D Full Bore Ball Valve data: Size (Inch), Area (mm2), Size (DN)
API6D_Valve = namedtuple('API6D_Valve', ['size_in', 'area_mm2', 'size_dn'])
Valve = namedtuple('Valve', ['area_m2', 'type', 'letter', 'area_mm2'])

logging.basicConfig(filename='blowdown_studio.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class UnitConverter:
    def __init__(self):
        self.pressure_map = {
            'pa': 1.0, 'kpa': 1e3, 'mpa': 1e6, 'bar': 1e5, 'psi': 6894.76, 'atm': 101325.0
        }
        self.temperature_map = {
            'k': lambda x: x, 'c': lambda x: x + 273.15, 'f': lambda x: (x - 32) * 5/9 + 273.15,
            'r': lambda x: x * 5/9
        }
        self.length_map = {
            'm': 1.0, 'mm': 0.001, 'cm': 0.01, 'in': 0.0254, 'ft': 0.3048
        }
        self.volume_map = {
            'm3': 1.0, 'l': 0.001, 'gal': 0.00378541, 'ft3': 0.0283168
        }
        self.mass_flow_units = {
            'kg/h': 1.0, 'lb/h': 0.453592,
        }
        self.flow_rate_map = {
            'scmh': 1.0,
            'mmscfd': 41666.67 / 35.3147,  # Approximately 1179.8 SCMH
        }
        
    def convert_pressure(self, value, unit_str, pressure_type='absolute'):
        unit = unit_str.lower().strip()
        
        if unit in ['bara', 'psia', 'atma']:
            base_unit = unit[:-1]
            pressure_type = 'absolute'
        elif unit in ['barg', 'psig', 'atmg']:
            base_unit = unit[:-1]
            pressure_type = 'gauge'
        else:
            base_unit = unit
            
        if base_unit not in self.pressure_map:
            raise ValueError(f"Geçersiz basınç birimi: {unit_str}")
            
        pa_value = value * self.pressure_map[base_unit]
        if pressure_type == 'gauge':
             return pa_value + P_ATM
        return pa_value

    def convert_pressure_from_pa(self, value_pa, unit_str):
        unit = unit_str.lower().strip()

        if unit in ['bara', 'psia', 'atma']:
            base_unit = unit[:-1]
            return value_pa / self.pressure_map[base_unit]
        if unit in ['barg', 'psig', 'atmg']:
            base_unit = unit[:-1]
            return (value_pa - P_ATM) / self.pressure_map[base_unit]
        if unit not in self.pressure_map:
            raise ValueError(f"Geçersiz basınç birimi: {unit_str}")
        return value_pa / self.pressure_map[unit]

    def convert_temperature(self, value, unit_str):
        unit = unit_str.lower().strip()
        if unit in self.temperature_map:
            return self.temperature_map[unit](value)
        raise ValueError(f"Geçersiz sıcaklık birimi: {unit_str}")

    def convert_length(self, value, unit_str):
         unit = unit_str.lower().strip()
         if unit in self.length_map:
             return value * self.length_map[unit]
         raise ValueError(f"Geçersiz uzunluk birimi: {unit_str}")

    def convert_volume(self, value, unit_str):
        unit = unit_str.lower().strip()
        if unit in self.volume_map:
            return value * self.volume_map[unit]
        raise ValueError(f"Geçersiz hacim birimi: {unit_str}")

    def convert_mass_flow_to_kg_h(self, value, unit_str):
        unit = unit_str.lower().strip()
        if unit == 'kg/h':
            return value
        if unit == 'lb/h':
            return value * 0.453592
        if unit == 'kg/s':
            return value * 3600.0
        raise ValueError(f"Geçersiz kütlesel debi birimi: {unit_str}")

    def convert_liquid_flow_to_l_min(self, value, unit_str):
        unit = unit_str.lower().strip()
        if unit == 'l/min':
            return value
        if unit == 'm3/h':
            return value * 1000.0 / 60.0
        if unit == 'gpm':
            return value * 3.78541
        raise ValueError(f"Geçersiz sıvı hacimsel debi birimi: {unit_str}")

    def convert_flow_rate_to_kg_h(self, value, unit_str, composition):
        unit = unit_str.lower().strip()
        
        # Mass Flow
        if unit in ['kg/h', 'lb/h', 'kg/s']:
            return self.convert_mass_flow_to_kg_h(value, unit_str)
        
        # Volumetric Flow
        MW_mix_kg_kmol = sum(CP.PropsSI('M', g) * f for g, f in composition.items()) * 1000.0
        
        t_std = 273.15
        p_std = 101325.0
        scmh = 0
        
        if unit in ['nm3/h', 'scmh']:
            scmh = value
            t_std = 273.15
        elif unit == 'sm3/h':
            scmh = value
            t_std = 288.15
        elif unit == 'scfm':
            scmh = value * 1.6990
            t_std = 288.71
        elif unit == 'mmscfd':
            scmh = value * 1179.86
            t_std = 288.71
        else:
            raise ValueError(f"Geçersiz debi birimi: {unit_str}")
            
        mass_flow_kg_h = scmh * (p_std * MW_mix_kg_kmol) / (R_U * t_std)
        return mass_flow_kg_h

    def convert_area(self, value, unit_str):
        unit = unit_str.lower().strip()
        area_map = {'m2': 1.0, 'mm2': 1e-6, 'cm2': 1e-4, 'in2': 0.00064516, 'ft2': 0.092903}
        if unit in area_map:
            return value * area_map[unit]
        raise ValueError(f"Geçersiz alan birimi: {unit_str}")

    def convert_mass(self, value, unit_str):
        unit = unit_str.lower().strip()
        mass_map = {'kg': 1.0, 'g': 0.001, 'lb': 0.453592, 'ton': 1000.0}
        if unit in mass_map:
            return value * mass_map[unit]
        raise ValueError(f"Geçersiz kütle birimi: {unit_str}")

def load_api526_data():
    # Returns Orifice Letter, Area (in2), Area (mm2), Size (Inch), Size (DN)
    return [
        API526_Orifice('D', 0.110, 71.0, '1" x 2"', 'DN25 x DN50'),
        API526_Orifice('E', 0.196, 126.5, '1" x 2" / 1.5" x 2.5"', 'DN25 x DN50 / DN40 x DN65'),
        API526_Orifice('F', 0.307, 198.1, '1.5" x 2.5" / 2" x 3"', 'DN40 x DN65 / DN50 x DN80'),
        API526_Orifice('G', 0.503, 324.5, '2" x 3"', 'DN50 x DN80'),
        API526_Orifice('H', 0.785, 506.5, '2" x 3" / 3" x 4"', 'DN50 x DN80 / DN80 x DN100'),
        API526_Orifice('J', 1.287, 830.3, '3" x 4"', 'DN80 x DN100'),
        API526_Orifice('K', 1.838, 1185.8, '3" x 4" / 4" x 6"', 'DN80 x DN100 / DN100 x DN150'),
        API526_Orifice('L', 2.853, 1840.6, '4" x 6"', 'DN100 x DN150'),
        API526_Orifice('M', 3.600, 2322.6, '4" x 6"', 'DN100 x DN150'),
        API526_Orifice('N', 4.340, 2800.0, '4" x 6"', 'DN100 x DN150'),
        API526_Orifice('P', 6.380, 4116.1, '4" x 6" / 6" x 8"', 'DN100 x DN150 / DN150 x DN200'),
        API526_Orifice('Q', 11.050, 7129.0, '6" x 8" / 8" x 10"', 'DN150 x DN200 / DN200 x DN250'),
        API526_Orifice('R', 16.000, 10322.6, '6" x 8" / 8" x 10"', 'DN150 x DN200 / DN200 x DN250'),
        API526_Orifice('T', 26.000, 16774.2, '8" x 10"', 'DN200 x DN250'),
    ]

def load_api6d_data():
    # Standard Full Bore Ball Valve Areas (Approximate based on nominal ID)
    # Using A = (pi/4) * D^2
    return [
        API6D_Valve('1"', 506.7, 'DN25'),
        API6D_Valve('1.5"', 1140.1, 'DN40'),
        API6D_Valve('2"', 2026.8, 'DN50'),
        API6D_Valve('3"', 4560.4, 'DN80'),
        API6D_Valve('4"', 8107.3, 'DN100'),
        API6D_Valve('6"', 18241.5, 'DN150'),
        API6D_Valve('8"', 32429.3, 'DN200'),
        API6D_Valve('10"', 50670.7, 'DN250'),
        API6D_Valve('12"', 72965.9, 'DN300'),
        API6D_Valve('14"', 100000.0, 'DN350'), # Approx
        API6D_Valve('16"', 130000.0, 'DN400'),
        API6D_Valve('18"', 165000.0, 'DN450'),
        API6D_Valve('20"', 205000.0, 'DN500'),
        API6D_Valve('24"', 295000.0, 'DN600'),
    ]

# ---------------------------------------------------------
# LOGGING HANDLER
# ---------------------------------------------------------

class TkinterHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.text_widget.tag_config("INFO", foreground="black")
        self.text_widget.tag_config("WARNING", foreground="orange")
        self.text_widget.tag_config("ERROR", foreground="red")
        self.text_widget.tag_config("CRITICAL", foreground="red", underline=1)

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, msg + "\n", record.levelname)
            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)
        self.text_widget.after(0, append)

def find_psv_area_by_flow_rate(inputs):

    """
    Legacy helper kept for backward compatibility.
    `p0_pa` is treated as relieving pressure input for this compatibility path.
    """
    warnings.warn(
        "find_psv_area_by_flow_rate() deprecated; use calculate_preliminary_gas_psv_area() instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    legacy_inputs = {
        'composition': inputs['composition'],
        'W_req_kg_h': float(inputs['W_req_kg_h']),
        'set_pressure_pa': float(inputs['p0_pa']),
        'mawp_pa': float(inputs.get('p0_pa', inputs['p0_pa'])),
        'overpressure_pct': 0.0,
        'relieving_temperature_k': float(inputs['T0_k']),
        'p_total_backpressure_pa': float(inputs.get('p_downstream', P_ATM)),
        'Kd_api520': float(inputs.get('Kd_api520', inputs.get('Kd', inputs.get('Cd', 0.975)))),
        'Kb': inputs.get('Kb'),
        'Kc': float(inputs.get('Kc', 1.0)),
        'prv_design': str(inputs.get('prv_design', 'Conventional')),
    }

    sizing = calculate_preliminary_gas_psv_area(legacy_inputs)

    return (
        sizing.A_req_m2,
        sizing.is_critical,
        sizing.k_ideal,
        sizing.MW_kg_kmol,
        sizing.h_relieving_j_kg,
        sizing.Z,
        sizing.critical_pressure_ratio,
        sizing.rho_relieving_kg_m3,
    )

# ---------------------------------------------------------
# Backward-compatible aliases for older scripts/tests.
run_blowdown_simulation_v3 = run_native_blowdown_simulation
find_blowdown_area_v3 = find_native_blowdown_area

# UI & APPLICATION
# ---------------------------------------------------------

class Application(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(f"{APP_NAME} - {APP_VERSION}")
        self.geometry("1200x820")
        self.minsize(1024, 768)
        self.converter = UnitConverter()
        
        try:
            self.available_gases = sorted(CP.get_global_param_string('FluidsList').split(','))
        except:
            self.available_gases = ['Methane', 'Ethane', 'Propane', 'N2', 'H2', 'CO2']
        
        self.composition = {}
        self.user_inputs = {}
        self.last_blowdown_report_bundle = None
        self.last_psv_report_bundle = None
        self.vendor_catalog_path = None
        self.abort_flag = threading.Event()
        self.create_widgets()
        self.setup_logging()
        
        # Start auto-update check in background
        self.check_for_updates(manual=False)

    def setup_logging(self):
        handler = TkinterHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def create_widgets(self):
        build_menu_bar(self)
        build_application_shell_ui(self)
        self.create_right_pane(self.right_pane)
        self.create_left_pane(self.left_container)
        self.create_api2000_pane(self.api2000_tab)

    def check_for_updates(self, manual=False):
        return start_update_check_async(
            current_version=APP_VERSION,
            manual=manual,
            fetch_latest_release_fn=fetch_latest_release,
            is_update_available_fn=is_update_available,
            schedule_ui_fn=lambda callback: self.after(0, callback),
            prompt_update_fn=self._prompt_update,
            show_up_to_date_fn=lambda: messagebox.showinfo("Güncelleme Kontrolü", f"Programınız şu an en güncel sürümdedir ({APP_VERSION})."),
            show_connection_error_fn=lambda: messagebox.showerror("Hata", "Güncelleme sunucusuna bağlanılamadı. Lütfen internet bağlantınızı kontrol edin."),
            logger=logging,
        )

    def _prompt_update(self, latest_version, release_data):
        return prompt_and_start_update_download(
            current_version=APP_VERSION,
            latest_version=latest_version,
            release_data=release_data,
            prompt_update_download_path_fn=lambda current, latest, data: prompt_update_download_path(
                current,
                latest,
                data,
                default_path_fn=default_update_download_path,
                choose_path_fn=choose_update_download_path,
            ),
            start_update_download_fn=self._start_update_download,
        )

    def _start_update_download(self, release_data, save_path, release_page=""):
        del release_page
        start_update_download_async(
            release_data,
            save_path,
            schedule_ui=lambda callback: self.after(0, callback),
            set_progress_text=lambda text: self.progress_label.config(text=text),
            show_info=messagebox.showinfo,
            show_error=messagebox.showerror,
            logger=logging.getLogger(__name__),
        )
            
    def create_left_pane(self, parent):
        build_left_pane_ui(self, parent)

    def create_right_pane(self, parent):
        build_right_pane_ui(self, parent)

    def _show_graph_placeholder(self, mode_text):
        if not hasattr(self, "fig") or not hasattr(self, "canvas"):
            return
        draw_graph_placeholder(self.fig, mode_text)
        self.canvas.draw()

    def create_main_settings(self, frame):
        build_main_settings_ui(
            self,
            frame,
            app_version=APP_VERSION,
            native_engine_name=NATIVE_ENGINE_NAME,
            segmented_engine_name=SEGMENTED_ENGINE_NAME,
            two_phase_engine_name=TWO_PHASE_ENGINE_NAME,
        )

    def _set_field_label(self, field_name, label_text):
        set_field_label(self, field_name, label_text)

    def _set_unit_options(self, field_name, units, default_unit):
        set_unit_options(self, field_name, units, default_unit)

    def _configure_psv_service_fields(self):
        return configure_psv_service_fields(self, build_psv_service_field_config)

    def on_mode_change(self, event=None):
        apply_mode_change(
            self,
            app_version=APP_VERSION,
            native_engine_name=NATIVE_ENGINE_NAME,
            state_builder=build_mode_ui_state,
            service_field_config_builder=build_psv_service_field_config,
            placeholder_callback=self._show_graph_placeholder,
        )

    def handle_run_button(self):
        dispatch_run(
            self.mode_combo.get(),
            blowdown_fn=self.start_calculation_thread,
            psv_fn=self.run_psv_sizing,
        )

    def run_psv_sizing(self):
        return run_psv_ui_flow_with_feedback(
            self,
            converter=self.converter,
            collect_payload_fn=collect_psv_ui_payload,
            get_active_vendor_catalog_fn=self._get_active_vendor_catalog,
            execute_workflow_fn=execute_psv_workflow,
            apply_result_fn=apply_psv_workflow_result,
            load_api526_data=load_api526_data,
            load_api6d_data=load_api6d_data,
            set_status_text_fn=self.update_results_text,
            refresh_ui_fn=self.update_idletasks,
            showerror_fn=messagebox.showerror,
        )


    def create_gas_settings(self, frame):
        build_gas_settings_ui(self, frame, self.available_gases)
        
    def filter_gas_list(self, event=None):
        del event
        filter_gas_listbox(self.gas_listbox, self.available_gases, self.gas_search_entry.get())

    def add_gas(self):
        add_selected_gas(
            self.composition,
            self.gas_listbox,
            self.mole_entry,
            self.comp_text,
            showwarning_fn=messagebox.showwarning,
        )

    def clear_comp(self):
        clear_composition(self.composition, self.comp_text)

    def update_composition_display(self):
        render_composition_text(self.comp_text, self.composition)

    def abort_simulation(self):
        self.abort_flag.set()

    def get_inputs_from_ui(self):
        return collect_blowdown_inputs(
            self,
            converter=self.converter,
            fire_case_builder=build_pool_fire_case_screening,
            p_atm=P_ATM,
            segmented_engine_name=SEGMENTED_ENGINE_NAME,
            showwarning_fn=messagebox.showwarning,
        )

    def start_calculation_thread(self):
        return start_blowdown_thread(
            self,
            collect_inputs_fn=self.get_inputs_from_ui,
            run_logic_target=self.run_calculation_logic,
            logger=logging.getLogger(__name__),
            showerror_fn=messagebox.showerror,
        )

    def run_calculation_logic(self):
        self.last_blowdown_report_bundle = None
        return run_blowdown_ui_flow_with_feedback(
            user_inputs=self.user_inputs,
            native_engine_name=NATIVE_ENGINE_NAME,
            execute_flow_fn=execute_blowdown_ui_flow,
            update_progress_ui=self.update_progress_ui,
            abort_flag=self.abort_flag,
            load_api526_data=load_api526_data,
            load_api6d_data=load_api6d_data,
            size_area_fn=size_blowdown_area,
            select_standard_valve_fn=select_standard_valve,
            run_engine_fn=run_blowdown_engine,
            build_report_fn=build_blowdown_report,
            logger=logging,
            schedule_ui_fn=self.after,
            update_results_fn=self.update_results_text,
            plot_results_fn=self.plot_results,
            showerror_fn=messagebox.showerror,
            showwarning_fn=messagebox.showwarning,
            finalize_run_button_fn=lambda: self.btn_run.config(state=tk.NORMAL),
            finalize_abort_button_fn=lambda: self.btn_abort.config(state=tk.DISABLED),
            store_report_bundle_fn=lambda bundle: setattr(self, "last_blowdown_report_bundle", bundle),
        )

    def update_results_text(self, text):
        set_text_widget_content(self.results_text, text)

    def export_psv_csv(self):
        export_psv_report_with_feedback(
            self.last_psv_report_bundle,
            export_kind="csv",
            export_bundle_with_dialog_fn=lambda bundle, export_kind: export_psv_bundle_with_dialog(
                bundle,
                export_kind=export_kind,
                export_csv_fn=export_psv_report_csv,
                export_pdf_fn=export_psv_report_pdf,
            ),
            show_result_fn=show_psv_export_result,
            showwarning_fn=messagebox.showwarning,
            showerror_fn=messagebox.showerror,
        )

    def export_blowdown_csv(self):
        export_blowdown_report_with_feedback(
            self.last_blowdown_report_bundle,
            export_kind="csv",
            export_bundle_with_dialog_fn=lambda bundle, export_kind: export_blowdown_bundle_with_dialog(
                bundle,
                export_kind=export_kind,
                export_csv_fn=export_blowdown_report_csv,
                export_pdf_fn=export_blowdown_report_pdf,
            ),
            show_result_fn=show_blowdown_export_result,
            showwarning_fn=messagebox.showwarning,
            showerror_fn=messagebox.showerror,
        )

    def export_blowdown_pdf(self):
        export_blowdown_report_with_feedback(
            self.last_blowdown_report_bundle,
            export_kind="pdf",
            export_bundle_with_dialog_fn=lambda bundle, export_kind: export_blowdown_bundle_with_dialog(
                bundle,
                export_kind=export_kind,
                export_csv_fn=export_blowdown_report_csv,
                export_pdf_fn=export_blowdown_report_pdf,
            ),
            show_result_fn=show_blowdown_export_result,
            showwarning_fn=messagebox.showwarning,
            showerror_fn=messagebox.showerror,
        )

    def export_psv_pdf(self):
        export_psv_report_with_feedback(
            self.last_psv_report_bundle,
            export_kind="pdf",
            export_bundle_with_dialog_fn=lambda bundle, export_kind: export_psv_bundle_with_dialog(
                bundle,
                export_kind=export_kind,
                export_csv_fn=export_psv_report_csv,
                export_pdf_fn=export_psv_report_pdf,
            ),
            show_result_fn=show_psv_export_result,
            showwarning_fn=messagebox.showwarning,
            showerror_fn=messagebox.showerror,
        )

    def _get_active_vendor_catalog(self):
        return get_active_vendor_catalog(self.vendor_catalog_path)

    def import_vendor_catalog(self):
        file_path = import_vendor_catalog_dialog(
            askopenfilename_fn=filedialog.askopenfilename,
            load_with_summary_fn=load_vendor_catalog_with_summary,
            format_loaded_message_fn=format_vendor_catalog_loaded_message,
            showinfo_fn=messagebox.showinfo,
            showerror_fn=messagebox.showerror,
        )
        if file_path:
            self.vendor_catalog_path = file_path

    def reset_vendor_catalog(self):
        self.vendor_catalog_path = reset_vendor_catalog_dialog(showinfo_fn=messagebox.showinfo)

    def show_vendor_catalog_summary(self):
        return show_vendor_catalog_summary_dialog(
            self.vendor_catalog_path,
            get_summary_fn=get_active_vendor_catalog_summary,
            format_summary_message_fn=format_vendor_catalog_summary_message,
            showinfo_fn=messagebox.showinfo,
            showerror_fn=messagebox.showerror,
        )

    def update_progress_ui(self, current, target, text=""):
        self.after(0, lambda: update_progress_widgets(self.progress, self.progress_label, current, target, text))

    def plot_results(self, sim_df, inputs, valve):
        return self.plot_blowdown_results(sim_df, inputs, valve)

    def plot_blowdown_results(self, sim_df, inputs, valve):
        render_blowdown_plots(self.fig, sim_df, inputs, valve)
        draw_figure_on_tab(self.fig, self.canvas, self.notebook, self.graphs_tab)

    def plot_psv_graphs(self, sizing, inputs, selected_valve, valve_data, vendor_selection, vendor_evaluation, force_N_design, valve_count):
        render_psv_plots(
            self.fig,
            sizing,
            inputs,
            selected_valve,
            valve_data,
            vendor_selection,
            vendor_evaluation,
            force_N_design,
            valve_count,
            self.valve_type_combo.get(),
        )
        draw_figure_on_tab(self.fig, self.canvas, self.notebook, self.graphs_tab)
        return


    def save_settings(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            data = build_settings_payload(self)
            write_settings_payload(file_path, data)
            messagebox.showinfo("Başarılı", "Ayarlar kaydedildi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydetme başarısız: {e}")

    def load_settings(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            data = read_settings_payload(file_path)
            apply_settings_payload(self, data, default_engine_name=NATIVE_ENGINE_NAME)
            messagebox.showinfo("Başarılı", "Ayarlar yüklendi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Yükleme başarısız: {e}")

    def create_api2000_pane(self, parent):
        build_api2000_pane_ui(self, parent)
        
    def run_api2000_calculation(self):
        run_api2000_ui_with_feedback(
            self,
            run_workflow_fn=run_api2000_workflow,
            set_text_fn=lambda text: set_text_widget_content(self.api_results_text, text, readonly=False),
            log_info_fn=logging.info,
            showerror_fn=messagebox.showerror,
        )

    def show_methodology(self):
        content = build_methodology_text(
            native_engine_name=NATIVE_ENGINE_NAME,
            segmented_engine_name=SEGMENTED_ENGINE_NAME,
            two_phase_engine_name=TWO_PHASE_ENGINE_NAME,
        )
        show_methodology_dialog(self, content)

if __name__ == "__main__":
    Application().mainloop()

