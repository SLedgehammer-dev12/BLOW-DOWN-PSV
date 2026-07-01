import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import CoolProp.CoolProp as CP
import logging
from collections import namedtuple
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
import threading
import os
import math

# Constants and Data Structures
R_U = 8314.462618  # Universal gas constant (J/kmol·K)
P_ATM = 101325     # Standard atmospheric pressure (Pa)
T_STD = 288.7      # Standard temperature (288.7 K = 60°F)

API526_Orifice = namedtuple('API526_Orifice', ['letter', 'area_in2', 'area_mm2'])
Valve = namedtuple('Valve', ['area_m2', 'type', 'letter', 'area_mm2'])

logging.basicConfig(filename='blowdown_sim_v3.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class UnitConverter:
    def __init__(self):
        self.pressure_map = {
            'pa': 1.0, 'kpa': 1e3, 'bar': 1e5, 'psi': 6894.76
        }
        self.temperature_map = {
            'k': lambda x: x, 'c': lambda x: x + 273.15, 'f': lambda x: (x - 32) * 5/9 + 273.15
        }
        self.length_map = {
            'm': 1.0, 'mm': 0.001, 'cm': 0.01, 'in': 0.0254, 'ft': 0.3048
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

    def convert_length(self, value, unit_str):
         unit = unit_str.lower().strip()
         if unit in self.length_map:
             return value * self.length_map[unit]
         raise ValueError(f"Geçersiz uzunluk birimi: {unit_str}")

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
        API526_Orifice('D', 0.110, 71.0), API526_Orifice('E', 0.196, 126.5),
        API526_Orifice('F', 0.307, 198.1), API526_Orifice('G', 0.503, 324.5),
        API526_Orifice('H', 0.785, 506.5), API526_Orifice('J', 1.287, 830.3),
        API526_Orifice('K', 1.838, 1185.8), API526_Orifice('L', 2.853, 1840.6),
        API526_Orifice('M', 3.600, 2322.6), API526_Orifice('N', 4.340, 2800.0),
        API526_Orifice('P', 6.380, 4116.1), API526_Orifice('Q', 11.050, 7129.0),
        API526_Orifice('R', 16.000, 10322.6), API526_Orifice('T', 26.000, 16774.2),
    ]

# ---------------------------------------------------------
# THERMODYNAMIC & HEAT TRANSFER ENGINE (V3)
# ---------------------------------------------------------

def calculate_flow_rate(area_m2, p1_pa, t1_k, k, Z, MW, is_choked=True, p_downstream=P_ATM, Cd=0.975):
    if is_choked:
        W_kg_s = Cd * area_m2 * p1_pa * math.sqrt(k * MW / (Z * R_U * t1_k)) * (2 / (k + 1))**((k + 1) / (2 * (k - 1)))
        W_kg_h = W_kg_s * 3600
    else:
        beta = p_downstream / p1_pa
        # Subcritical mass flow rate
        radicand = max(1e-9, beta**(2/k) - beta**((k+1)/k))
        W_kg_s = Cd * area_m2 * p1_pa * math.sqrt((2 * k * MW) / ((k - 1) * Z * R_U * t1_k)) * math.sqrt(radicand)
        W_kg_h = W_kg_s * 3600
    return W_kg_h

def get_h_inner(T_gas, T_wall, P_gas, state):
    """
    Calculates internal free convection (h_inner) using Nusselt, Prandtl, Grashof.
    Simplified characteristic length (L_char) logic applied for typical piping.
    """
    try:
        cond = state.conductivity() # W/m.K
        visc = state.viscosity()    # Pa.s
        cp = state.cpmass()         # J/kg.K
        rho = state.rhomass()       # kg/m3
        Pr = cp * visc / cond
        beta = state.isobaric_expansion_coefficient() # 1/K
        nu = visc / rho
        L_char = 1.0 # Assume characteristic length of 1 meter for free convection correlations
        
        dT = abs(T_wall - T_gas)
        if dT < 0.1: dT = 0.1
        
        Gr = 9.81 * beta * dT * (L_char**3) / (nu**2)
        Ra = Pr * Gr
        
        # Nusselt Number for free convection
        if Ra >= 1e9:
            Nu = 0.13 * (Ra ** 0.333)
        elif Ra > 1e4:
            Nu = 0.59 * (Ra ** 0.25)
        else:
            Nu = 1.36 * (Ra ** 0.20)
            
        h_inner = Nu * cond / L_char
        # Cap abnormal values
        return min(max(h_inner, 2.0), 300.0)
    except Exception as e:
        return 10.0 # Safe fallback

def run_blowdown_simulation_v3(inputs, vana_alani_m2, progress_callback=None, abort_flag=None, silent=False):
    """
    1st Law of Thermodynamics (Energy Balance) approach to depressurisation.
    Corresponds to HydDown's energy tracking method to solve Metal Temperature (MDMT).
    """
    V_sys = inputs['V_sys']
    p_sys = inputs['p0_pa']
    T_sys = inputs['T0_k']
    T_wall = inputs['T0_k'] # Metal begins at same temp as fluid
    comp = inputs['composition']
    target_pressure = inputs['p_target_blowdown_pa']
    target_time = inputs['t_target_sec']
    
    A_inner = inputs['A_inner']
    M_steel = inputs['M_steel']
    Cp_steel = 480.0 # J/kg.K for Carbon Steel
    
    p_downstream = P_ATM
    zaman_serisi = []
    
    # Create AbstractState for internal U/H tracking
    state = CP.AbstractState("HEOS", "&".join(comp.keys()))
    state.set_mole_fractions(list(comp.values()))
    state.update(CP.PT_INPUTS, p_sys, T_sys)
    
    U_mass = state.umass() # Initial internal energy J/kg
    m_fluid = p_sys * V_sys / (state.compressibility_factor() * (R_U / (state.molar_mass()*1000)) * T_sys)
    MW = state.molar_mass() * 1000 # kg/kmol
    Z = state.compressibility_factor()
    
    t = 0
    dt = max(0.1, target_time / 1000.0) 
    max_t = target_time * 5.0
    dm_kg_s = 0.0
    
    while p_sys > target_pressure:
        if abort_flag and abort_flag.is_set():
             return None
             
        try:
             # Fast state params for discharge calculations
             state.update(CP.DmassUmass_INPUTS, m_fluid/V_sys, U_mass)
             p_sys = state.p()
             T_sys = state.T()
             k = state.cpmass() / state.cvmass()
             Z = state.compressibility_factor()
             H_mass = state.hmass()
        except Exception as e:
             try:
                 # Mixture fallback using Explicit PT_INPUTS update
                 dU_mass = U_mass - state.umass()
                 try:
                     cv = state.cvmass()
                     if math.isnan(cv) or cv <= 0: cv = 1700.0
                 except: cv = 1700.0
                     
                 T_new = T_sys + (dU_mass / cv)
                 
                 rho_new = m_fluid / V_sys
                 p_guess = Z * rho_new * (R_U / MW) * T_new
                 
                 state.update(CP.PT_INPUTS, p_guess, T_new)
                 
                 p_sys = state.p()
                 T_sys = state.T()
                 try: k = state.cpmass() / state.cvmass()
                 except: k = 1.3
                 try: Z = state.compressibility_factor()
                 except: Z = 0.9
                 try: H_mass = state.hmass()
                 except: H_mass = U_mass + p_sys / rho_new
             except Exception as inner_e:
                 # Complete fallback to ideal tracking
                 T_sys = T_new if 'T_new' in locals() and not math.isnan(T_new) else T_sys
                 p_sys = p_guess if 'p_guess' in locals() and not math.isnan(p_guess) else p_sys
                 k = 1.3
                 Z = 0.9
                 H_mass = U_mass + p_sys / (m_fluid / V_sys)
             
        if p_sys <= target_pressure:
            break
            
        pr_crit = (2 / (k + 1))**(k / (k - 1))
        is_choked = (p_downstream / p_sys) <= pr_crit
        
        W_kg_h = calculate_flow_rate(vana_alani_m2, p_sys, T_sys, k, Z, MW, is_choked, p_downstream)
        dm_kg_s = W_kg_h / 3600.0
        
        # 1. Heat Transfer (Convection Gas -> Wall)
        h_in = get_h_inner(T_sys, T_wall, p_sys, state)
        Q_in_watts = h_in * A_inner * (T_wall - T_sys) # Heat enters gas FROM wall
        
        # 2. Wall Temp Differential
        dT_wall = (-Q_in_watts * dt) / (M_steel * Cp_steel)
        T_wall += dT_wall
        
        # 3. Fluid Mass Differential
        old_m = m_fluid
        m_fluid = max(1e-6, m_fluid - dm_kg_s * dt)
        
        # 4. Fluid Energy Differential (1st Law)
        # dU_total = Q_in - H_out*dm_out
        U_total_old = (U_mass * old_m)
        U_total_new = U_total_old + (Q_in_watts * dt) - (H_mass * dm_kg_s * dt)
        U_mass = U_total_new / m_fluid
        
        t += dt
        
        if not silent:
            zaman_serisi.append({'t': t, 'p_sys': p_sys, 'mdot_kg_s': dm_kg_s, 'T_sys': T_sys, 'T_wall': T_wall, 'h_in': h_in})
            if progress_callback and int(t/dt) % 20 == 0: 
                progress_callback(t, target_time)

        if t > max_t:
            break
            
    if silent:
        return t
    else:
        zaman_serisi.append({'t': t, 'p_sys': p_sys, 'mdot_kg_s': dm_kg_s, 'T_sys': T_sys, 'T_wall': T_wall, 'h_in': getattr(locals(), 'h_in', 10)})
        return pd.DataFrame(zaman_serisi)

def find_blowdown_area_v3(inputs, progress_callback=None, abort_flag=None):
    logging.info("Iterative alan arama başlatıldı (V3 - Enerji Balansı)...")
    target_time = inputs['t_target_sec']
    A_low, A_high = 1e-6, 1.0
    max_iter = 30
    tolerance = 0.05 
    
    for i in range(max_iter):
        if abort_flag and abort_flag.is_set(): return None
        A_mid = (A_low + A_high) / 2.0
        if progress_callback: progress_callback(i, max_iter, text="Süre Optimizasyonu (İterasyon)...")
        
        sim_time = run_blowdown_simulation_v3(inputs, A_mid, silent=True)
        if sim_time is None: return None
        
        if abs(sim_time - target_time) / target_time <= tolerance:
            return A_mid
        if sim_time > target_time: A_low = A_mid
        else: A_high = A_mid
            
    return A_mid

# ---------------------------------------------------------
# UI & APPLICATION (V3)
# ---------------------------------------------------------

class Application(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Blowdown Simülasyonu - V3 (Pipeline & Isı Transferi)")
        self.geometry("1000x850")
        self.converter = UnitConverter()
        
        try:
            self.available_gases = sorted(CP.get_global_param_string('FluidsList').split(','))
        except:
            self.available_gases = ['Methane', 'Ethane', 'Propane', 'N2', 'H2', 'CO2']
        
        self.composition = {}
        self.user_inputs = {}
        self.abort_flag = threading.Event()
        self.create_widgets()
    
    def create_widgets(self):
        # Menu
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Ayarları Yükle", command=self.load_settings)
        filemenu.add_command(label="Ayarları Kaydet", command=self.save_settings)
        filemenu.add_separator()
        filemenu.add_command(label="Çıkış", command=self.quit)
        menubar.add_cascade(label="Dosya", menu=filemenu)
        self.config(menu=menubar)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, expand=True, fill="both", padx=10)
        
        self.input_frame = ttk.Frame(self.notebook)
        self.results_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.input_frame, text="Giriş Parametreleri")
        self.notebook.add(self.results_frame, text="Grafikler ve Analiz Sonuçları")
        
        self.input_frame.columnconfigure(0, weight=1)
        self.input_frame.columnconfigure(1, weight=1)
        self.input_frame.rowconfigure(0, weight=1)
        
        self.main_frame = ttk.Frame(self.input_frame)
        self.gas_frame = ttk.Frame(self.input_frame)
        
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.gas_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.create_main_settings(self.main_frame)
        self.create_gas_settings(self.gas_frame)
        
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(8, 10))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.results_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def create_main_settings(self, frame):
        ttk.Label(frame, text="Sistem Tipi:").grid(row=0, column=0, padx=5, sticky="w")
        self.sys_type_combo = ttk.Combobox(frame, values=["Boru Hattı (Pipeline)", "Tank (Vessel)"], state="readonly")
        self.sys_type_combo.grid(row=0, column=1, padx=5, sticky="ew")
        self.sys_type_combo.set("Boru Hattı (Pipeline)")
        
        geom_frame = ttk.LabelFrame(frame, text="Geometri ve Proses Şartları (Gerekli)")
        geom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        geom_frame.columnconfigure(1, weight=1)
        
        self.entries = {}
        labels = [
            "İç Çap (mm):", "Uzunluk (m):", "Et Kalınlığı (mm):", 
            "Başlangıç Basıncı (barg):", "Başlangıç Sıcaklığı (C):",
            "Hedef Blowdown Süresi (s):", "Hedef Blowdown Basıncı (barg):"
        ]
        
        for i, text in enumerate(labels):
            ttk.Label(geom_frame, text=text).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            entry = ttk.Entry(geom_frame)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            self.entries[text] = entry

        self.btn_run = ttk.Button(frame, text="V3 Analizini Başlat (Enerji Balansı + MDMT)", command=self.start_calculation_thread)
        self.btn_run.grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")
        
        self.btn_abort = ttk.Button(frame, text="Durdur", state=tk.DISABLED, command=self.abort_simulation)
        self.btn_abort.grid(row=4, column=0, columnspan=2, pady=5, sticky="ew")
        
        self.progress_label = ttk.Label(frame, text="")
        self.progress_label.grid(row=5, column=0, columnspan=2)
        
        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        self.progress.grid(row=6, column=0, columnspan=2, pady=5, sticky="ew")
        
        frame.columnconfigure(1, weight=1)

    def create_gas_settings(self, frame):
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Gaz Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.gas_combo = ttk.Combobox(frame, values=self.available_gases)
        self.gas_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(frame, text="Mol Fraksiyonu:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mol_frac_entry = ttk.Entry(frame)
        self.mol_frac_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        
        self.btn_add_gas = ttk.Button(btn_frame, text="Gaz Ekle", command=self.add_gas)
        self.btn_add_gas.grid(row=0, column=0, padx=5, sticky="ew")
        self.btn_remove_gas = ttk.Button(btn_frame, text="Gazı Çıkar", command=self.remove_gas)
        self.btn_remove_gas.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.comp_listbox = tk.Listbox(frame, height=15)
        self.comp_listbox.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        frame.rowconfigure(3, weight=1)

    def add_gas(self):
        gas, frac = self.gas_combo.get(), self.mol_frac_entry.get()
        try:
            self.composition[gas] = float(frac)
            self.update_composition_listbox()
        except: pass
    
    def remove_gas(self):
        selected = self.comp_listbox.curselection()
        if selected:
            del self.composition[self.comp_listbox.get(selected[0]).split(":")[0].strip()]
            self.update_composition_listbox()

    def update_composition_listbox(self):
        self.comp_listbox.delete(0, tk.END)
        for gas, frac in self.composition.items():
            self.comp_listbox.insert(tk.END, f"{gas}: {frac}")

    def abort_simulation(self):
        self.abort_flag.set()

    def get_inputs_from_ui(self):
        inputs = {'composition': self.composition}
        if not inputs['composition']: raise ValueError("Lütfen en az 1 gaz ekleyin.")

        def pf(k): return float(self.entries[k].get())
        
        D_in_m = self.converter.convert_length(pf("İç Çap (mm):"), 'mm')
        L_m = pf("Uzunluk (m):") # Directly in M
        t_m = self.converter.convert_length(pf("Et Kalınlığı (mm):"), 'mm')
        
        inputs['V_sys'] = math.pi * ((D_in_m/2)**2) * L_m
        inputs['A_inner'] = math.pi * D_in_m * L_m
        
        # Calculate Mass of steel
        v_outer = math.pi * (((D_in_m + 2*t_m)/2)**2) * L_m
        v_metal = v_outer - inputs['V_sys']
        inputs['M_steel'] = v_metal * 7850.0 # kg
        
        inputs['p0_pa'] = self.converter.convert_pressure(pf("Başlangıç Basıncı (barg):"), 'barg', 'gauge')
        inputs['T0_k'] = self.converter.convert_temperature(pf("Başlangıç Sıcaklığı (C):"), 'c')
        
        inputs['p_target_blowdown_pa'] = self.converter.convert_pressure(pf("Hedef Blowdown Basıncı (barg):"), 'barg', 'gauge')
        inputs['t_target_sec'] = pf("Hedef Blowdown Süresi (s):")
        
        if inputs['p_target_blowdown_pa'] >= inputs['p0_pa']:
             raise ValueError("Hedef Basınç, Başlangıçtan küçük olmalı.")
             
        inputs['valve_count'] = 1
        return inputs

    def start_calculation_thread(self):
        try:
            self.user_inputs = self.get_inputs_from_ui()
            total = sum(self.user_inputs['composition'].values())
            self.user_inputs['composition'] = {k: v/total for k,v in self.user_inputs['composition'].items()}
            
            self.btn_run["state"] = tk.DISABLED
            self.btn_abort["state"] = tk.NORMAL
            self.abort_flag.clear()
            threading.Thread(target=self.run_calculation_logic, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def run_calculation_logic(self):
        try:
            A_req_m2 = find_blowdown_area_v3(self.user_inputs, self.update_progress_ui, self.abort_flag)
            if A_req_m2 is None: return
                
            selected_valve = next((v for v in load_api526_data() if v.area_mm2 >= A_req_m2*1e6), None)
            v_area = (selected_valve.area_mm2/1e6) if selected_valve else A_req_m2
            
            self.update_progress_ui(0, 100, "V3 Sonuç Profili İşleniyor...")
            sim_df = run_blowdown_simulation_v3(self.user_inputs, v_area, self.update_progress_ui, self.abort_flag, silent=False)
            
            if sim_df is not None:
                self.after(0, self.plot_results, sim_df, self.user_inputs, selected_valve)
        finally:
            self.after(0, lambda: self.btn_run.config(state=tk.NORMAL))
            self.after(0, lambda: self.btn_abort.config(state=tk.DISABLED))

    def update_progress_ui(self, current, target, text=""):
        def update():
            if target > 0: self.progress["value"] = (current/target)*100
            if text: self.progress_label["text"] = text
        self.after(0, update)

    def plot_results(self, sim_df, inputs, valve):
        self.ax1.clear(); self.ax2.clear(); self.ax3.clear()
        
        # Pressure
        self.ax1.plot(sim_df['t'], sim_df['p_sys'] / 1e5, color='blue')
        self.ax1.set_ylabel('Basınç (bara)'); self.ax1.grid(True)
        self.ax1.set_title("V3 Blowdown Simülasyonu (Boru Hattı / MDMT)")
        
        # Temperatures
        self.ax2.plot(sim_df['t'], sim_df['T_sys'] - 273.15, label='İç Akışkan (Gaz) Sıc.', color='orange')
        self.ax2.plot(sim_df['t'], sim_df['T_wall'] - 273.15, label='Metal Duvar (MDMT)', color='red', linewidth=2)
        self.ax2.set_ylabel('Sıcaklık (°C)'); self.ax2.legend(); self.ax2.grid(True)
        
        # Convection
        self.ax3.plot(sim_df['t'], sim_df['h_in'], label='İç Konveksiyon h (W/m²K)', color='green')
        self.ax3.set_ylabel('Isı Transfer Ksh.'); self.ax3.set_xlabel('Zaman (s)'); self.ax3.grid(True)
        
        self.fig.tight_layout()
        self.canvas.draw()
        self.notebook.select(self.results_frame)

    def save_settings(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            data = {
                'system_type': self.sys_type_combo.get(),
                'entries': {k: v.get() for k, v in self.entries.items()},
                'composition': self.composition
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Başarılı", "Ayarlar kaydedildi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydetme başarısız: {e}")

    def load_settings(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.sys_type_combo.set(data.get('system_type', "Boru Hattı (Pipeline)"))
            for k, val in data.get('entries', {}).items():
                if k in self.entries:
                    self.entries[k].delete(0, tk.END)
                    self.entries[k].insert(0, str(val))
            self.composition = data.get('composition', {})
            self.update_composition_listbox()
            messagebox.showinfo("Başarılı", "Ayarlar yüklendi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Yükleme başarısız: {e}")

if __name__ == "__main__":
    Application().mainloop()
