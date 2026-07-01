import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import CoolProp.CoolProp as CP
import logging
from collections import namedtuple
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
import threading
import os
import time

# Constants and Data Structures
R_U = 8314.462618  # Universal gas constant (J/kmol·K)
P_ATM = 101325     # Standard atmospheric pressure (Pa)
T_STD = 288.7      # Standard temperature (288.7 K = 60°F)
T_STD_C = 273.15   # 0°C and 1 atm

API526_Orifice = namedtuple('API526_Orifice', ['letter', 'area_in2', 'area_mm2'])
Valve = namedtuple('Valve', ['area_m2', 'type', 'letter', 'area_mm2'])

logging.basicConfig(filename='blowdown_sim_v2.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class UnitConverter:
    def __init__(self):
        self.pressure_map = {
            'pa': 1.0, 'kpa': 1e3, 'bar': 1e5, 'psi': 6894.76
        }
        self.temperature_map = {
            'k': lambda x: x, 'c': lambda x: x + 273.15, 'f': lambda x: (x - 32) * 5/9 + 273.15
        }
        self.volume_map = {
            'm3': 1.0, 'l': 1e-3, 'ft3': 0.0283168
        }
        self.mass_flow_units = {
            'kg/h': 1.0,
            'lb/h': 0.453592,
        }
        self.flow_rate_map = {
            'scmh': 1.0,
            'mmscfd': 41666.67 / 35.3147,  # Approximately 1179.8 SCMH
        }
        
    def convert_pressure(self, value, unit_str, pressure_type='absolute'):
        unit = unit_str.lower().strip()
        base_unit = unit.replace('a', '').replace('g', '')
        
        if base_unit not in self.pressure_map:
            raise ValueError(f"Geçersiz basınç birimi: {unit_str}")
        
        pa_value = value * self.pressure_map[base_unit]

        if pressure_type == 'gauge' or unit_str.endswith('g'):
            return pa_value + P_ATM
        return pa_value

    def convert_temperature(self, value, unit_str):
        unit = unit_str.lower().strip()
        if unit in self.temperature_map:
            return self.temperature_map[unit](value)
        raise ValueError(f"Geçersiz sıcaklık birimi: {unit_str}")

    def convert_volume(self, value, unit_str):
        unit = unit_str.lower().strip()
        if unit in self.volume_map:
            return value * self.volume_map[unit]
        raise ValueError(f"Geçersiz hacim birimi: {unit_str}")
    
    def convert_mass_flow(self, value, unit_str):
        unit = unit_str.lower().strip()
        if unit in self.mass_flow_units:
            return value * self.mass_flow_units[unit]
        raise ValueError(f"Geçersiz kütle akış birimi: {unit_str}")
    
    def convert_volumetric_flow_to_mass(self, value, unit_str, composition):
        unit = unit_str.lower().strip()
        
        if unit == 'mmscfd':
            T_std_k = 288.7
            P_std_pa = P_ATM
            scmh_value = value * 1179.86
        else:
            T_std_k = 273.15
            P_std_pa = P_ATM
            scmh_value = value * self.flow_rate_map.get(unit, 1.0)
            
        MW_mix = sum(CP.PropsSI('M', g) * f for g, f in composition.items()) * 1000
        mass_flow_kg_h = scmh_value * (P_std_pa * MW_mix) / (R_U * T_std_k)
        
        return mass_flow_kg_h

def load_api526_data():
    return [
        API526_Orifice('D', 0.110, 71.0),
        API526_Orifice('E', 0.196, 126.5),
        API526_Orifice('F', 0.307, 198.1),
        API526_Orifice('G', 0.503, 324.5),
        API526_Orifice('H', 0.785, 506.5),
        API526_Orifice('J', 1.287, 830.3),
        API526_Orifice('K', 1.838, 1185.8),
        API526_Orifice('L', 2.853, 1840.6),
        API526_Orifice('M', 3.600, 2322.6),
        API526_Orifice('N', 4.340, 2800.0),
        API526_Orifice('P', 6.380, 4116.1),
        API526_Orifice('Q', 11.050, 7129.0),
        API526_Orifice('R', 16.000, 10322.6),
        API526_Orifice('T', 26.000, 16774.2),
    ]

def get_gas_properties(p_pa, t_k, composition):
    try:
        gas_state = CP.AbstractState("HEOS", "&".join(composition.keys()))
        gas_state.set_mole_fractions(list(composition.values()))
        gas_state.update(CP.PT_INPUTS, p_pa, t_k)
        k = gas_state.gamma()
        Z = gas_state.compressibility_factor()
        MW = gas_state.molar_mass() * 1000 # kg/kmol
    except Exception as e:
        logging.error(f"CoolProp Error: {e}. Falling back to ideal gas assumption.")
        MW = sum(CP.PropsSI('M', g) for g in composition.keys()) * 1000
        k = 1.4
        Z = 1.0
    Rs = R_U / MW
    return k, Z, MW, Rs

def calculate_flow_rate(area_m2, p1_pa, t1_k, k, Z, MW, is_choked=True, p_downstream=P_ATM, Cd=0.975):
    # Flow rate equation based on fundamental thermodynamics & API 520
    if is_choked:
        # W = C_d * A * P1 * sqrt(k * M / (Z * R * T1)) * (2 / (k+1))^((k+1) / (2*(k-1)))
        W_kg_s = Cd * area_m2 * p1_pa * np.sqrt(k * MW / (Z * R_U * t1_k)) * (2 / (k + 1))**((k + 1) / (2 * (k - 1)))
        W_kg_h = W_kg_s * 3600
    else: # Subcritical
        beta = p_downstream / p1_pa
        # Subcritical mass flow rate
        W_kg_s = Cd * area_m2 * p1_pa * np.sqrt((2 * k * MW) / ((k - 1) * Z * R_U * t1_k)) * np.sqrt(beta**(2/k) - beta**((k+1)/k))
        W_kg_h = W_kg_s * 3600
    return W_kg_h

def calculate_psv_area(inputs):
    W_kg_h = inputs['W_kg_h']
    p1_pa = inputs['p_relieving_pa']
    t1_k = inputs['T0_k']
    comp = inputs['composition']
    
    k, Z, MW, Rs = get_gas_properties(p1_pa, t1_k, comp)
    
    # API 520 Part 1 - Sizing for Critical Flow (Gas/Vapor)
    Cd = 0.975
    Kb = 1.0 # Backpressure correction (assuming atmospheric discharge so = 1)
    Kc = 1.0 # Combination correction factor
    
    # Isentropic expansion coefficient C (for SI Units: W in kg/h, A in mm2, P in kPa)
    # C = 0.03948 * sqrt(k * (2/(k+1))^((k+1)/(k-1)))
    C_coef = 0.03948 * np.sqrt(k * (2 / (k + 1))**((k + 1) / (k - 1)))
    p1_kpa = p1_pa / 1000.0
    
    A_req_mm2 = W_kg_h / (C_coef * Cd * p1_kpa * Kb * Kc) * np.sqrt(t1_k * Z / MW)
    A_req_m2 = A_req_mm2 / 1e6
    
    logging.info(f"PSV için hesaplanan orifis alanı (API 520): {A_req_m2:.6f} m^2")
    return A_req_m2

def select_valve_size(A_req_m2, valve_count):
    api_data = load_api526_data()
    A_req_mm2 = (A_req_m2 * 1e6) / valve_count
    
    for orifice in api_data:
        if orifice.area_mm2 >= A_req_mm2:
            logging.info(f"Gerekli alan {A_req_mm2:.2f} mm² için, {valve_count} adet '{orifice.letter}' Orifis vana yeterli.")
            return Valve(orifice.area_mm2/1e6 * valve_count, 'PSV', orifice.letter, orifice.area_mm2)
            
    logging.error(f"Gerekli alanı ({A_req_mm2:.2f} mm²) karşılayacak standart vana boyutu bulunamadı. Muhtemelen birden fazla vana gerekli.")
    return None

def run_blowdown_simulation(inputs, vana_alani_m2, progress_callback=None, abort_flag=None, silent=False):
    V_sys, p_sys, T_sys, comp = inputs['V_sys'], inputs['p0_pa'], inputs['T0_k'], inputs['composition']
    p_target, t_target = inputs['p_target_blowdown_pa'], inputs['t_target_sec']
    zaman_serisi = []
    
    # Ensure dt is not too small to slow things down, not too large to be inaccurate
    dt = max(0.1, t_target / 1000.0) 
    t = 0
    max_t = t_target * 5.0 # Stop early if it takes 5x the target time
    
    while p_sys > p_target:
        if abort_flag and abort_flag.is_set():
            if not silent: logging.info("Simülasyon kullanıcı tarafından durduruldu.")
            return None
            
        k, Z, MW, Rs = get_gas_properties(p_sys, T_sys, comp)
        pr_crit = (2 / (k + 1))**(k / (k - 1))
        is_choked = (P_ATM / p_sys) <= pr_crit
        
        W_kg_h = calculate_flow_rate(vana_alani_m2, p_sys, T_sys, k, Z, MW, is_choked, p_downstream=P_ATM, Cd=0.975)
        m_eski = p_sys * V_sys / (Z * Rs * T_sys)
        dm_kg_s = W_kg_h / 3600
        m_yeni = max(1e-6, m_eski - dm_kg_s * dt)

        T_sys_yeni = T_sys * (m_yeni / m_eski)**(k-1)
        p_sys_yeni = p_sys * (m_yeni / m_eski)**k
        
        p_sys, T_sys, t = p_sys_yeni, T_sys_yeni, t + dt
        
        if not silent:
            zaman_serisi.append({'t': t, 'p_sys': p_sys, 'mdot_kg_s': dm_kg_s, 'T_sys': T_sys})
            if progress_callback and int(t/dt) % 20 == 0: 
                progress_callback(t, t_target)

        if t > max_t:
            break
            
    if not silent: logging.info(f"Simülasyon tamamlandı. Geçen süre: {t:.2f} s")
    
    if silent:
        return t
    else:
        return pd.DataFrame(zaman_serisi)

def find_blowdown_area(inputs, progress_callback=None, abort_flag=None):
    """
    Iterative solver (Bisection method) to find the required area for blowdown
    to reach target pressure in target time.
    """
    logging.info("Iterative alan arama başlatıldı...")
    target_time = inputs['t_target_sec']
    p_target = inputs['p_target_blowdown_pa']
    p0 = inputs['p0_pa']
    
    if p_target >= p0:
        raise ValueError("Hedef basınç, başlangıç basıncından küçük olmalıdır.")
        
    A_low = 1e-6    # Çok küçük vana = Çok uzun süre
    A_high = 1.0    # Çok büyük vana = Çok kısa süre
    
    max_iter = 30
    tolerance = 0.05 # 5% zaman toleransı
    
    for i in range(max_iter):
        if abort_flag and abort_flag.is_set():
            return None
            
        A_mid = (A_low + A_high) / 2.0
        
        if progress_callback: progress_callback(i, max_iter, text="Vana Alanı İterasyonu yapılıyor...")
        
        sim_time = run_blowdown_simulation(inputs, A_mid, silent=True)
        
        if sim_time is None: return None # Aborted
        
        if abs(sim_time - target_time) / target_time <= tolerance:
            logging.info(f"İterasyon başarılı. Alan: {A_mid:.6f} m^2, Süre: {sim_time:.2f} s")
            return A_mid
            
        if sim_time > target_time:
            # Vana yetersiz, süreyi aştı -> Alanı büyüt
            A_low = A_mid
        else:
            # Vana çok büyük, erken bitirdi -> Alanı küçült
            A_high = A_mid
            
    logging.warning(f"İterasyon max limite ulaştı. Tahmini alan: {A_mid:.6f}")
    return A_mid

class Application(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("PSV / Blowdown Simülasyonu - V2 (API 520/521/526)")
        self.geometry("900x800")
        self.converter = UnitConverter()
        
        try:
            self.available_gases = sorted(CP.get_global_param_string('FluidsList').split(','))
        except Exception as e:
            logging.error(f"CoolProp'tan gaz listesi alınamadı. Hata: {e}")
            self.available_gases = ['Methane', 'Ethane', 'Propane', 'N2', 'H2', 'CO2', 'C2H4']
        
        self.composition = {}
        self.user_inputs = {}
        self.simulation_thread = None
        self.abort_flag = threading.Event()
        self.create_widgets()
    
    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, expand=True, fill="both")
        
        self.main_frame = ttk.Frame(self.notebook)
        self.gas_frame = ttk.Frame(self.notebook)
        self.results_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.main_frame, text="Ana Ayarlar")
        self.notebook.add(self.gas_frame, text="Gaz Kompozisyonu")
        self.notebook.add(self.results_frame, text="Sonuçlar ve Grafikler")
        
        self.create_main_settings(self.main_frame)
        self.create_gas_settings(self.gas_frame)
        
        # Prepare Results Figure setup
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.results_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_main_settings(self, frame):
        ttk.Label(frame, text="Cihaz Tipi:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.cihaz_tipi_combo = ttk.Combobox(frame, values=["PSV", "BLOWDOWN"])
        self.cihaz_tipi_combo.current(0)
        self.cihaz_tipi_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.cihaz_tipi_combo.bind("<<ComboboxSelected>>", self.update_fields_for_cihaz)
        
        self.entries = {}
        labels = ["Sistem Hacmi (m3):", "Başlangıç Basıncı (barg):", "Başlangıç Sıcaklığı (C):"]
        
        for i, text in enumerate(labels, start=1):
            ttk.Label(frame, text=text).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            entry = ttk.Entry(frame)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            self.entries[text] = entry
        
        self.psv_frame = ttk.LabelFrame(frame, text="PSV Ayarları")
        self.blowdown_frame = ttk.LabelFrame(frame, text="Blowdown (Depressurization) Ayarları")
        
        self.update_fields_for_cihaz()

        self.btn_run = ttk.Button(frame, text="Hesaplamayı Başlat", command=self.start_calculation_thread)
        self.btn_run.grid(row=10, column=0, columnspan=2, pady=10)
        
        self.btn_abort = ttk.Button(frame, text="Durdur", state=tk.DISABLED, command=self.abort_simulation)
        self.btn_abort.grid(row=11, column=0, columnspan=2, pady=5)
        
        self.progress_label = ttk.Label(frame, text="")
        self.progress_label.grid(row=12, column=0, columnspan=2)
        
        self.progress = ttk.Progressbar(frame, orient="horizontal", length=250, mode="determinate")
        self.progress.grid(row=13, column=0, columnspan=2, pady=5)

    def create_gas_settings(self, frame):
        ttk.Label(frame, text="Gaz Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.gas_combo = ttk.Combobox(frame, values=self.available_gases)
        self.gas_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(frame, text="Mol Fraksiyonu (veya %):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mol_frac_entry = ttk.Entry(frame)
        self.mol_frac_entry.grid(row=1, column=1, padx=5, pady=5)
        
        self.btn_add_gas = ttk.Button(frame, text="Gaz Ekle", command=self.add_gas)
        self.btn_add_gas.grid(row=2, column=0, padx=5, pady=5)
        
        self.btn_remove_gas = ttk.Button(frame, text="Gazı Çıkar", command=self.remove_gas)
        self.btn_remove_gas.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(frame, text="Mevcut Kompozisyon:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.comp_listbox = tk.Listbox(frame, width=50, height=10)
        self.comp_listbox.grid(row=4, column=0, columnspan=2, padx=5, pady=5)
    
    def update_fields_for_cihaz(self, event=None):
        for widget in self.psv_frame.winfo_children(): widget.destroy()
        for widget in self.blowdown_frame.winfo_children(): widget.destroy()
        self.psv_frame.grid_remove()
        self.blowdown_frame.grid_remove()
        
        cihaz_tipi = self.cihaz_tipi_combo.get()
        
        if cihaz_tipi == "PSV":
            self.psv_frame.grid(row=5, column=0, columnspan=2, fill="x", padx=5, pady=5)
            labels = ["Set Basıncı (barg):", "Aşırı Basınç Oranı (%):", "Gerekli Tahliye Debisi (kg/h):"]
            self.entries["PSV_Inputs"] = {}
            for i, text in enumerate(labels):
                ttk.Label(self.psv_frame, text=text).grid(row=i, column=0, padx=5, pady=5, sticky="w")
                entry = ttk.Entry(self.psv_frame)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
                self.entries["PSV_Inputs"][text] = entry
                
        elif cihaz_tipi == "BLOWDOWN":
            self.blowdown_frame.grid(row=5, column=0, columnspan=2, fill="x", padx=5, pady=5)
            labels = ["Hedef Basınç (barg):", "Hedef Süre (s):"]
            self.entries["BLOWDOWN_Inputs"] = {}
            for i, text in enumerate(labels):
                ttk.Label(self.blowdown_frame, text=text).grid(row=i, column=0, padx=5, pady=5, sticky="w")
                entry = ttk.Entry(self.blowdown_frame)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
                self.entries["BLOWDOWN_Inputs"][text] = entry

    def add_gas(self):
        gas = self.gas_combo.get()
        frac = self.mol_frac_entry.get()
        try:
            val = float(frac)
            self.composition[gas] = val
            self.update_composition_listbox()
        except ValueError:
            messagebox.showwarning("Uyarı", "Geçerli bir mol fraksiyonu giriniz.")
    
    def remove_gas(self):
        selected = self.comp_listbox.curselection()
        if not selected:
            return
        gas_to_remove = self.comp_listbox.get(selected[0]).split(":")[0].strip()
        if gas_to_remove in self.composition:
            del self.composition[gas_to_remove]
        self.update_composition_listbox()

    def update_composition_listbox(self):
        self.comp_listbox.delete(0, tk.END)
        for gas, frac in self.composition.items():
            self.comp_listbox.insert(tk.END, f"{gas}: {frac}")

    def abort_simulation(self):
        self.abort_flag.set()
        self.btn_abort["state"] = tk.DISABLED
        self.progress_label["text"] = "Durduruluyor..."

    def get_inputs_from_ui(self):
        inputs = {}
        inputs['cihaz_tipi'] = self.cihaz_tipi_combo.get()
        inputs['composition'] = self.composition
        
        if not inputs['composition']:
            raise ValueError("Lütfen gaz kompozisyonu (en az 1 gaz) ekleyin.")

        # Safely get parsing with error throwing
        def parse_float(key, entry_dict):
            val = entry_dict[key].get().strip()
            if not val:
                raise ValueError(f"'{key}' alanı boş bırakılamaz.")
            try:
                return float(val)
            except ValueError:
                raise ValueError(f"'{key}' sayısal bir değer olmalıdır.")

        inputs['V_sys'] = self.converter.convert_volume(parse_float("Sistem Hacmi (m3):", self.entries), 'm3')
        
        # We take barg and compute absolute Pa
        p0_barg = parse_float("Başlangıç Basıncı (barg):", self.entries)
        inputs['p0_pa'] = self.converter.convert_pressure(p0_barg, 'barg', 'gauge')
        
        T0_c = parse_float("Başlangıç Sıcaklığı (C):", self.entries)
        inputs['T0_k'] = self.converter.convert_temperature(T0_c, 'c')
        
        if inputs['cihaz_tipi'] == "PSV":
            psv_entries = self.entries["PSV_Inputs"]
            p_set_barg = parse_float("Set Basıncı (barg):", psv_entries)
            inputs['p_set_pa'] = self.converter.convert_pressure(p_set_barg, 'barg', 'gauge')
            
            overpressure_perc = parse_float("Aşırı Basınç Oranı (%):", psv_entries)
            # Correcting API 520 Overpressure calculation over the gauge pressure!
            p_relieving_barg = p_set_barg * (1.0 + overpressure_perc / 100.0)
            inputs['p_relieving_pa'] = self.converter.convert_pressure(p_relieving_barg, 'barg', 'gauge')
            
            inputs['W_kg_h'] = parse_float("Gerekli Tahliye Debisi (kg/h):", psv_entries)
            
        elif inputs['cihaz_tipi'] == "BLOWDOWN":
            bd_entries = self.entries["BLOWDOWN_Inputs"]
            p_target_barg = parse_float("Hedef Basınç (barg):", bd_entries)
            inputs['p_target_blowdown_pa'] = self.converter.convert_pressure(p_target_barg, 'barg', 'gauge')
            inputs['t_target_sec'] = parse_float("Hedef Süre (s):", bd_entries)
            
            if inputs['p_target_blowdown_pa'] >= inputs['p0_pa']:
                 raise ValueError("Hedef Basınç, Başlangıç Basıncından DAHA DÜŞÜK olmalıdır.")
            
        inputs['valve_count'] = 1
        return inputs

    def normalize_composition(self, comp):
        total = sum(comp.values())
        return {g: f / total for g, f in comp.items()}

    def start_calculation_thread(self):
        try:
            self.user_inputs = self.get_inputs_from_ui()
            self.user_inputs['composition'] = self.normalize_composition(self.user_inputs['composition'])
            
            self.btn_run["state"] = tk.DISABLED
            self.btn_abort["state"] = tk.NORMAL
            self.progress["value"] = 0
            self.abort_flag.clear()
            
            self.simulation_thread = threading.Thread(target=self.run_calculation_logic, daemon=True)
            self.simulation_thread.start()
        except ValueError as ve:
            messagebox.showerror("Girdi Hatası", str(ve))
            logging.error(f"Girdi hatası: {ve}")

    def run_calculation_logic(self):
        inputs = self.user_inputs
        try:
            A_req_m2 = 0
            selected_valve = None
            sim_df = None
            
            if inputs['cihaz_tipi'] == "PSV":
                self.update_progress_ui(10, 100, "Vana alanı hesaplanıyor...")
                A_req_m2 = calculate_psv_area(inputs)
                selected_valve = select_valve_size(A_req_m2, inputs['valve_count'])
                if selected_valve:
                    msg = f"API 520 Hesaplanan Alan: {A_req_m2*1e6:.2f} mm²\nAPI 526 Standart Seçilen Orifis: {selected_valve.letter} (Alan: {selected_valve.area_mm2} mm²)"
                    self.after(0, lambda: messagebox.showinfo("Hesaplama Sonucu", msg))
                    self.update_progress_ui(100, 100, "Hesaplama Tamamlandı.")
                
            elif inputs['cihaz_tipi'] == "BLOWDOWN":
                A_req_m2 = find_blowdown_area(inputs, self.update_progress_ui, self.abort_flag)
                
                if A_req_m2 is None:  # Aborted
                    self.update_progress_ui(0, 100, "İptal Edildi.")
                    return
                    
                selected_valve = select_valve_size(A_req_m2, inputs['valve_count'])
                
                # Run actual simulation with final selected valve to plot graphs
                if selected_valve:
                    msg = f"Iteratif Alan İhtiyacı: {A_req_m2*1e6:.2f} mm²\nSeçilen API 526 Vana: {selected_valve.letter} ({selected_valve.area_mm2} mm²)"
                    self.after(0, lambda: messagebox.showinfo("Gerekli Vana Bulundu", msg))
                    
                    self.update_progress_ui(0, 100, "Final Simülasyon Profili Çıkartılıyor...")
                    sim_df = run_blowdown_simulation(inputs, selected_valve.area_m2, self.update_progress_ui, self.abort_flag, silent=False)
                    
                    if sim_df is not None:
                        # Schedule plotting on the MAIN thread
                        self.after(0, self.plot_results, sim_df, inputs, selected_valve)
                        file_path = self.generate_report(inputs, sim_df, A_req_m2, selected_valve)
                        self.after(0, lambda: messagebox.showinfo("Rapor Oluşturuldu", f"Pdf Rapor: '{file_path}'"))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Hata", f"Hesaplama sırasında hata oluştu:\n{e}"))
            logging.error(f"Hesaplama hatası (Logic): {e}", exc_info=True)
            
        finally:
            self.after(0, self.reset_ui_state)

    def reset_ui_state(self):
        self.btn_run["state"] = tk.NORMAL
        self.btn_abort["state"] = tk.DISABLED
        if not self.abort_flag.is_set():
            self.progress["value"] = 100
            self.progress_label["text"] = "İşlem Tamamlandı"

    def update_progress_ui(self, current, target, text=""):
        # We must use self.after to mutate tkinter widgets from separate thread
        def update():
            if target > 0:
                pct = (current / target) * 100
                self.progress["value"] = pct
            if text:
                self.progress_label["text"] = text
        self.after(0, update)

    def plot_results(self, sim_df, inputs, selected_valve):
        # Clear existing axes
        self.ax1.clear()
        self.ax2.clear()
        
        self.ax1.plot(sim_df['t'], sim_df['p_sys'] / 1e5, label='Sistem Basıncı (bara)', color='blue', linewidth=2)
        if inputs['cihaz_tipi'] == "BLOWDOWN":
            self.ax1.axhline(inputs['p_target_blowdown_pa'] / 1e5, color='red', linestyle='--', label='Hedef Basınç (bara)')
            self.ax1.axvline(x=inputs['t_target_sec'], color='green', linestyle='--', label='Hedef Süre')
        
        self.ax1.set_title(f"Dinamik Blowdown Tahliyesi - API 526 Orifis: {selected_valve.letter}")
        self.ax1.set_xlabel('Zaman (s)')
        self.ax1.set_ylabel('Basınç (bara)')
        self.ax1.legend()
        self.ax1.grid(True)
        
        self.ax2.plot(sim_df['t'], sim_df['mdot_kg_s'] * 3600, label='Kütlesel Tahliye Debisi (kg/h)', color='orange', linewidth=2)
        self.ax2.set_xlabel('Zaman (s)')
        self.ax2.set_ylabel('Debi (kg/h)')
        self.ax2.legend()
        self.ax2.grid(True)
        
        self.fig.tight_layout()
        self.canvas.draw()
        
        self.notebook.select(self.results_frame)

    def generate_report(self, inputs, sim_df, A_req_m2, selected_valve):
        report_filename = f"V2_Report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        doc = SimpleDocTemplate(report_filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Paragraph("<b>Mühendislik Analiz Raporu - Versiyon 2 (API 520/521/526)</b>", styles['h1']))
        story.append(Paragraph(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("<b>1. Kullanıcı Girişleri</b>", styles['h2']))
        data = [["Parametre", "Değer"],
                ["Cihaz Tipi", inputs['cihaz_tipi']],
                ["Sistem Hacmi", f"{inputs['V_sys']:.2f} m³"],
                ["Başlangıç Basıncı", f"{inputs['p0_pa']/1e5:.2f} bara"],
                ["Başlangıç Sıcaklığı", f"{inputs['T0_k']:.2f} K"]]
        story.append(Table(data, style=TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black)])))

        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>2. Hesaplama Sonuçları</b>", styles['h2']))
        results_data = [
            ["Gerekli Orifis Alanı", f"{A_req_m2*1e6:.2f} mm²"],
            ["API 526 Vana Harfi", f"{selected_valve.letter} (x{inputs['valve_count']})"],
            ["Sağlanan Toplam Alan", f"{selected_valve.area_mm2*inputs['valve_count']:.2f} mm²"]
        ]
        if inputs['cihaz_tipi'] == "BLOWDOWN":
            results_data.extend([["Hedef Tahliye Süresi", f"{inputs['t_target_sec']} s"],
                                 ["API 526 Alanı ile Ulaşılan Süre (Hedefe varış)", f"{sim_df['t'].iloc[-1]:.2f} s"]])
                                 
        story.append(Table(results_data, style=TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black)])))
        
        # Save current plot to image
        img_path = "temp_plot_v2.png"
        self.fig.savefig(img_path)
        
        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>3. Sonuç Grafikleri</b>", styles['h2']))
        story.append(Image(img_path, width=450, height=350))
        
        doc.build(story)
        if os.path.exists(img_path):
            os.remove(img_path)
        return report_filename

def main():
    app = Application()
    app.mainloop()

if __name__ == "__main__":
    main()
