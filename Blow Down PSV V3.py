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
from api2000_engine import calculate_api2000_venting

# Constants and Data Structures
R_U = 8314.462618  # Universal gas constant (J/kmol·K)
P_ATM = 101325     # Standard atmospheric pressure (Pa)
T_STD = 288.7      # Standard temperature (288.7 K = 60°F)

API526_Orifice = namedtuple('API526_Orifice', ['letter', 'area_in2', 'area_mm2', 'size_in', 'size_dn'])
# API 6D Full Bore Ball Valve data: Size (Inch), Area (mm2), Size (DN)
API6D_Valve = namedtuple('API6D_Valve', ['size_in', 'area_mm2', 'size_dn'])
Valve = namedtuple('Valve', ['area_m2', 'type', 'letter', 'area_mm2'])

logging.basicConfig(filename='blowdown_sim_v3.log', level=logging.INFO,
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

    def convert_flow_rate_to_kg_h(self, value, unit_str, composition):
        unit = unit_str.lower().strip()
        
        # Mass Flow
        if unit == 'kg/h': return value
        if unit == 'lb/h': return value * 0.453592
        if unit == 'kg/s': return value * 3600.0
        
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

# ---------------------------------------------------------
# THERMODYNAMIC & HEAT TRANSFER ENGINE (V3)
# ---------------------------------------------------------

def calculate_flow_rate(area_m2, p1_pa, t1_k, k, Z, MW, is_choked=True, p_downstream=P_ATM, Cd=0.975, Kb=1.0):
    if is_choked:
        W_kg_s = Cd * Kb * area_m2 * p1_pa * math.sqrt(k * MW / (Z * R_U * t1_k)) * (2 / (k + 1))**((k + 1) / (2 * (k - 1)))
        W_kg_h = W_kg_s * 3600
    else:
        beta = p_downstream / p1_pa
        # Subcritical mass flow rate
        radicand = max(1e-9, beta**(2/k) - beta**((k+1)/k))
        W_kg_s = Cd * Kb * area_m2 * p1_pa * math.sqrt((2 * k * MW) / ((k - 1) * Z * R_U * t1_k)) * math.sqrt(radicand)
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

def find_psv_area_by_flow_rate(inputs):
    """
    Directly calculates required orifice area using API 520 mass flow equation.
    inputs requires: 'W_req_kg_h', 'p0_pa', 'T0_k', 'composition', 'Cd', 'Kb'
    """
    W_kg_s = inputs['W_req_kg_h'] / 3600.0
    p_sys = inputs['p0_pa']
    T_sys = inputs['T0_k']
    comp = inputs['composition']
    p_downstream = P_ATM
    
    state = CP.AbstractState("HEOS", "&".join(comp.keys()))
    state.set_mole_fractions(list(comp.values()))
    state.update(CP.PT_INPUTS, p_sys, T_sys)
    
    k = state.cpmass() / state.cvmass()
    Z = state.compressibility_factor()
    MW = state.molar_mass() * 1000.0
    
    pr_crit = (2 / (k + 1))**(k / (k - 1))
    is_choked = (p_downstream / p_sys) <= pr_crit
    
    Cd = inputs.get('Cd', 0.975)
    Kb = inputs.get('Kb', 1.0)
    
    if is_choked:
        term1 = math.sqrt(k * MW / (Z * R_U * T_sys))
        term2 = (2 / (k + 1))**((k + 1) / (2 * (k - 1)))
        A_req_m2 = W_kg_s / (Cd * Kb * p_sys * term1 * term2)
    else:
        beta = p_downstream / p_sys
        radicand = max(1e-9, beta**(2/k) - beta**((k+1)/k))
        term1 = math.sqrt((2 * k * MW) / ((k - 1) * Z * R_U * T_sys))
        A_req_m2 = W_kg_s / (Cd * Kb * p_sys * term1 * math.sqrt(radicand))
        
    return A_req_m2, is_choked

def run_blowdown_simulation_v3(inputs, vana_alani_m2, progress_callback=None, abort_flag=None, silent=False):
    """
    1st Law of Thermodynamics (Energy Balance) approach to depressurisation.
    """
    V_sys = inputs['V_sys']
    p_sys = inputs['p0_pa']
    T_sys = inputs['T0_k']
    T_wall = inputs['T0_k']
    comp = inputs['composition']
    target_pressure = inputs['p_target_blowdown_pa']
    target_time = inputs['t_target_sec']
    
    HT_enabled = inputs.get('HT_enabled', True)
    
    A_inner = inputs.get('A_inner', 1.0)
    M_steel = inputs.get('M_steel', 100.0)
    Cp_steel = 480.0
    
    p_downstream = P_ATM
    zaman_serisi = []
    
    state = CP.AbstractState("HEOS", "&".join(comp.keys()))
    state.set_mole_fractions(list(comp.values()))
    state.update(CP.PT_INPUTS, p_sys, T_sys)
    
    U_mass = state.umass()
    MW = state.molar_mass() * 1000
    m_fluid = p_sys * V_sys / (state.compressibility_factor() * (R_U / MW) * T_sys)
    
    t = 0
    dt = max(0.01, min(0.5, target_time / 1000.0))
    max_t = target_time * 10.0
    
    # Unit Extended Factors
    Cd_val = inputs.get('Cd', 0.975)
    Kb_val = inputs.get('Kb', 1.0)
    
    p_old = p_sys
    
    while p_sys > target_pressure:
        if abort_flag and abort_flag.is_set():
            return None
            
        try:
            state.update(CP.DmassUmass_INPUTS, m_fluid/V_sys, U_mass)
            p_sys = state.p()
            T_sys = state.T()
            k = state.cpmass() / state.cvmass()
            Z = state.compressibility_factor()
            H_mass = state.hmass()
        except:
            # Emergency stability fallback
            p_sys *= 0.99
            T_sys *= 0.99
            k, Z, H_mass = 1.3, 0.9, U_mass + p_sys/(m_fluid/V_sys)
            
        if p_sys <= target_pressure: break
            
        pr_crit = (2 / (k + 1))**(k / (k - 1))
        is_choked = (p_downstream / p_sys) <= pr_crit
        
        W_kg_h = calculate_flow_rate(vana_alani_m2, p_sys, T_sys, k, Z, MW, is_choked, p_downstream, Cd=Cd_val, Kb=Kb_val)
        dm_kg_s = W_kg_h / 3600.0
        
        if HT_enabled:
            h_in = get_h_inner(T_sys, T_wall, p_sys, state)
            Q_in_watts = h_in * A_inner * (T_wall - T_sys)
            T_wall += (-Q_in_watts * dt) / (M_steel * Cp_steel)
        else:
            Q_in_watts = 0
            h_in = 0
            # T_wall remains at initial or follows gas (isothermal assumption)
        old_m = m_fluid
        m_fluid = max(1e-7, m_fluid - dm_kg_s * dt)
        U_mass = ( (U_mass * old_m) + (Q_in_watts * dt) - (H_mass * (old_m - m_fluid)) ) / m_fluid
        
        # Adaptive Time Stepping Logic (based on pressure change)
        dP = abs(p_sys - p_old) / p_sys
        p_old = p_sys
        if dP < 0.005: dt = min(dt * 1.2, 5.0)
        elif dP > 0.02: dt = max(dt / 1.5, 0.001)
        
        t += dt
        if not silent and progress_callback and int(t/max(0.001, dt)) % 20 == 0:
            progress_callback(t, target_time)
            
        if t > max_t: break
            
    if silent: return t
    return pd.DataFrame(zaman_serisi + [{'t': t, 'p_sys': p_sys, 'mdot_kg_s': dm_kg_s, 'T_sys': T_sys, 'T_wall': T_wall, 'h_in': h_in}])

def find_blowdown_area_v3(inputs, progress_callback=None, abort_flag=None):
    target_time = inputs['t_target_sec']
    A_low, A_high = 1e-8, 2.0
    max_iter = 35
    
    for i in range(max_iter):
        if abort_flag and abort_flag.is_set(): return None
        if progress_callback: progress_callback(i, max_iter, text=f"Boyutlandırma Analizi ({i+1}/{max_iter})...")
        
        A_mid = (A_low + A_high) / 2.0
        sim_time = run_blowdown_simulation_v3(inputs, A_mid, silent=True, abort_flag=abort_flag)
        
        if sim_time is None: return None
        if abs(sim_time - target_time) / target_time < 0.02: return A_mid
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
        self.setup_logging()

    def setup_logging(self):
        handler = TkinterHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def create_widgets(self):
        # Menu
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Ayarları Yükle", command=self.load_settings)
        filemenu.add_command(label="Ayarları Kaydet", command=self.save_settings)
        filemenu.add_separator()
        filemenu.add_command(label="Çıkış", command=self.quit)
        menubar.add_cascade(label="Dosya", menu=filemenu)
        
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Metodoloji (API 520/521/2000)", command=self.show_methodology)
        menubar.add_cascade(label="Yardım", menu=helpmenu)
        
        self.config(menu=menubar)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=5, expand=True, fill="both", padx=5)
        
        self.main_tab = ttk.Frame(self.notebook)
        self.api2000_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.main_tab, text="Blowdown Analizi")
        self.notebook.add(self.api2000_tab, text="Tank Havalandırma (API 2000)")
        self.notebook.add(self.log_tab, text="Loglar")

        # --- LOG TAB ---
        self.log_text = scrolledtext.ScrolledText(self.log_tab, state=tk.DISABLED, bg="white", font=("Consolas", 9))
        self.log_text.pack(expand=True, fill="both", padx=5, pady=5)

        # --- MAIN TAB (PanedWindow) ---
        self.paned = ttk.Panedwindow(self.main_tab, orient=tk.HORIZONTAL)
        self.paned.pack(expand=True, fill="both")

        self.left_pane = ttk.Frame(self.paned)
        self.right_pane = ttk.Frame(self.paned)
        self.paned.add(self.left_pane, weight=1)
        self.paned.add(self.right_pane, weight=2)

        # Left Pane: Inputs & Composition
        self.left_scroll = scrolledtext.ScrolledText(self.left_pane, bg="#f8f9fa") # Just container
        self.left_container = ttk.Frame(self.left_pane)
        self.left_container.pack(expand=True, fill="both", padx=5, pady=5)

        self.create_left_pane(self.left_container)
        self.create_right_pane(self.right_pane)
        self.create_api2000_pane(self.api2000_tab)

    def create_left_pane(self, parent):
        # Valve Type selection
        type_frame = ttk.LabelFrame(parent, text="Vana Seçimi")
        type_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(type_frame, text="Vana Standartı/Tipi:").pack(side="left", padx=5)
        self.valve_type_combo = ttk.Combobox(type_frame, values=["API 526 (PSV/PRV)", "API 6D (Küresel/Blowdown)"], state="readonly")
        self.valve_type_combo.pack(side="left", fill="x", expand=True, padx=5)
        self.valve_type_combo.set("API 526 (PSV/PRV)")

        # Main settings (inputs)
        self.main_settings_frame = ttk.Frame(parent)
        self.main_settings_frame.pack(fill="x", padx=5, pady=5)
        self.create_main_settings(self.main_settings_frame)

        # Gas settings (composition) - Below inputs
        self.gas_settings_frame = ttk.LabelFrame(parent, text="Gaz Kompozisyonu")
        self.gas_settings_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.create_gas_settings(self.gas_settings_frame)

    def create_right_pane(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        # Results Text
        self.results_text = tk.Text(parent, height=10, bg="#f0f0f0", font=("Consolas", 10))
        self.results_text.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.results_text.config(state=tk.DISABLED)

        # Graphs
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(6, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def create_main_settings(self, frame):
        # Mode Selection
        ttk.Label(frame, text="Analiz Modu:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.mode_combo = ttk.Combobox(frame, values=["Zamana Bağlı Basınç Düşürme (Blowdown)", "Gerekli Debiye Göre Emniyet Vanası Çapı (PSV Sizing)"], state="readonly")
        self.mode_combo.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.mode_combo.set("Zamana Bağlı Basınç Düşürme (Blowdown)")
        self.mode_combo.bind("<<ComboboxSelected>>", self.on_mode_change)

        self.sys_type_lbl = ttk.Label(frame, text="Sistem Tipi:")
        self.sys_type_lbl.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.sys_type_combo = ttk.Combobox(frame, values=["Boru Hattı (Pipeline)", "Tank (Vessel)"], state="readonly")
        self.sys_type_combo.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.sys_type_combo.set("Boru Hattı (Pipeline)")
        
        geom_frame = ttk.LabelFrame(frame, text="Geometri ve Proses Şartları")
        geom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        geom_frame.columnconfigure(1, weight=1)
        
        self.entries = {}
        self.unit_combos = {}
        self.entry_frames = {}
        
        inputs_config = [
            ("İç Çap", "mm", ["mm", "m", "cm", "in", "ft"]),
            ("Uzunluk", "m", ["m", "mm", "cm", "in", "ft"]),
            ("Et Kalınlığı", "mm", ["mm", "m", "cm", "in", "ft"]),
            ("Toplam Hacim", "m3", ["m3", "L", "gal", "ft3"]),
            ("Gerekli Tahliye Debisi", "kg/h", ["kg/h", "lb/h", "Nm3/h", "Sm3/h", "SCFM", "MMSCFD"]),
            ("Başlangıç Basıncı", "barg", ["barg", "bara", "psi", "psig", "atm", "Pa", "kPa", "MPa"]),
            ("Başlangıç Sıcaklığı", "C", ["C", "K", "F", "R"]),
            ("Hedef Blowdown Süresi", "s", ["s"]),
            ("Hedef Blowdown Basıncı", "barg", ["barg", "bara", "psi", "psig", "atm", "Pa", "kPa", "MPa"]),
            ("Vana Sayısı", "Adet", ["Adet"]),
            ("Discharge Coeff (Cd)", "", [""]),
            ("Backpressure Coeff (Kb)", "", [""])
        ]
        
        for i, (text, default_unit, units) in enumerate(inputs_config):
            lbl = ttk.Label(geom_frame, text=text + ":")
            lbl.grid(row=i, column=0, padx=5, pady=5, sticky="w")
            
            entry_frame = ttk.Frame(geom_frame)
            entry_frame.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            entry_frame.columnconfigure(0, weight=1)
            
            entry = ttk.Entry(entry_frame)
            entry.grid(row=0, column=0, sticky="ew")
            if text == "Vana Sayısı": entry.insert(0, "1")
            if text == "Discharge Coeff (Cd)": entry.insert(0, "0.975")
            if text == "Backpressure Coeff (Kb)": entry.insert(0, "1.0")
            self.entries[text] = entry
            
            combo = ttk.Combobox(entry_frame, values=units, state="readonly", width=8)
            combo.grid(row=0, column=1, padx=(5, 0))
            combo.set(default_unit)
            self.unit_combos[text] = combo
            
            self.entry_frames[text] = (lbl, entry_frame)

        self.ht_enabled_var = tk.BooleanVar(value=True)
        self.ht_check = ttk.Checkbutton(frame, text="Isıl Analiz (Heat Transfer) Aktif", variable=self.ht_enabled_var)
        self.ht_check.grid(row=3, column=0, columnspan=2, pady=5, sticky="w", padx=5)

        self.btn_run = ttk.Button(frame, text="V3 Analizini Başlat (Enerji Balansı + MDMT)", command=self.handle_run_button)
        self.btn_run.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        
        self.btn_abort = ttk.Button(frame, text="Durdur", state=tk.DISABLED, command=self.abort_simulation)
        self.btn_abort.grid(row=5, column=0, columnspan=2, pady=5, sticky="ew")
        
        self.progress_label = ttk.Label(frame, text="")
        self.progress_label.grid(row=6, column=0, columnspan=2)
        
        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        self.progress.grid(row=7, column=0, columnspan=2, pady=5, sticky="ew")
        
        # Initial UI setup
        self.on_mode_change()

    def on_mode_change(self, event=None):
        mode = self.mode_combo.get()
        if "Blowdown" in mode:
            for field in ["İç Çap", "Uzunluk", "Et Kalınlığı", "Toplam Hacim", "Hedef Blowdown Süresi", "Hedef Blowdown Basıncı"]:
                self.entry_frames[field][0].grid()
                self.entry_frames[field][1].grid()
            self.entry_frames["Gerekli Tahliye Debisi"][0].grid_remove()
            self.entry_frames["Gerekli Tahliye Debisi"][1].grid_remove()
            self.sys_type_combo.grid()
            self.sys_type_lbl.grid()
            self.ht_check.grid()
            self.btn_run.config(text="V3 Analizini Başlat (Enerji Balansı + MDMT)")
            self.btn_abort.grid()
            self.progress.grid()
            self.progress_label.grid()
        else:
            for field in ["İç Çap", "Uzunluk", "Et Kalınlığı", "Toplam Hacim", "Hedef Blowdown Süresi", "Hedef Blowdown Basıncı"]:
                self.entry_frames[field][0].grid_remove()
                self.entry_frames[field][1].grid_remove()
            self.entry_frames["Gerekli Tahliye Debisi"][0].grid()
            self.entry_frames["Gerekli Tahliye Debisi"][1].grid()
            self.sys_type_combo.grid_remove()
            self.sys_type_lbl.grid_remove()
            self.ht_check.grid_remove()
            self.btn_run.config(text="PSV Çapını Hesapla (API 520)")
            self.btn_abort.grid_remove()
            self.progress.grid_remove()
            self.progress_label.grid_remove()

    def handle_run_button(self):
        mode = self.mode_combo.get()
        if "Blowdown" in mode:
            self.start_calculation_thread()
        else:
            self.run_psv_sizing()

    def run_psv_sizing(self):
        try:
            self.results_text.config(state=tk.NORMAL)
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, "Hesaplanıyor... Lütfen bekleyin.\n\n")
            self.results_text.config(state=tk.DISABLED)
            self.update_idletasks()

            inputs = {'composition': self.composition}
            if not inputs['composition']: raise ValueError("Lütfen en az 1 gaz ekleyin.")
            
            # Normalize composition to 100%
            total_pct = sum(self.composition.values())
            inputs['composition'] = {k: v/total_pct for k,v in self.composition.items()}

            def get_val(key):
                val = self.entries[key].get().strip()
                return float(val) if val else None

            def get_unit(key):
                return self.unit_combos[key].get()

            flow_val = get_val("Gerekli Tahliye Debisi")
            p0_val = get_val("Başlangıç Basıncı")
            T0_val = get_val("Başlangıç Sıcaklığı")
            
            if flow_val is None or p0_val is None or T0_val is None:
                raise ValueError("Tahliye Debisi, Basınç ve Sıcaklık alanları zorunludur.")

            inputs['W_req_kg_h'] = self.converter.convert_flow_rate_to_kg_h(flow_val, get_unit("Gerekli Tahliye Debisi"), inputs['composition'])
            inputs['p0_pa'] = self.converter.convert_pressure(p0_val, get_unit("Başlangıç Basıncı"))
            inputs['T0_k'] = self.converter.convert_temperature(T0_val, get_unit("Başlangıç Sıcaklığı"))
            
            inputs['Cd'] = get_val("Discharge Coeff (Cd)") or 0.975
            inputs['Kb'] = get_val("Backpressure Coeff (Kb)") or 1.0

            A_req_m2, is_choked = find_psv_area_by_flow_rate(inputs)
            A_req_mm2 = A_req_m2 * 1e6

            valve_type = self.valve_type_combo.get()
            selected_valve = None
            
            if "API 526" in valve_type:
                api_data = load_api526_data()
                for orifice in api_data:
                    if orifice.area_mm2 >= A_req_mm2:
                        selected_valve = orifice
                        break
            else:
                api6d_data = load_api6d_valves()
                for v in api6d_data:
                    if v.area_m2 >= A_req_m2:
                        selected_valve = v
                        break

            self.results_text.config(state=tk.NORMAL)
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, "=== API 520 PSV ÇAP HESABI SONUÇLARI ===\n\n")
            self.results_text.insert(tk.END, f"Hesaplanan İdeal Orifis Alanı : {A_req_mm2:.2f} mm2\n")
            self.results_text.insert(tk.END, f"Akış Rejimi                 : {'Kritik (Choked)' if is_choked else 'Alt-Kritik (Subcritical)'}\n")
            self.results_text.insert(tk.END, f"Tahliye Debisi (Kütlesel)    : {inputs['W_req_kg_h']:.2f} kg/h\n\n")

            if selected_valve:
                self.results_text.insert(tk.END, "--- SEÇİLEN VANA ---\n")
                if "API 526" in valve_type:
                     self.results_text.insert(tk.END, f"Orifis Harfi       : {selected_valve.letter}\n")
                     self.results_text.insert(tk.END, f"Gerçek Vana Alanı  : {selected_valve.area_mm2:.1f} mm2\n")
                     self.results_text.insert(tk.END, f"Önerilen Flanş Tipi: {selected_valve.size_inch} ({selected_valve.size_dn})\n")
                else:
                     self.results_text.insert(tk.END, f"Vana Çapı (İç)     : {selected_valve.dn_size}\n")
                     self.results_text.insert(tk.END, f"Gerçek Vana Alanı  : {(selected_valve.area_m2 * 1e6):.1f} mm2\n")
            else:
                 self.results_text.insert(tk.END, "Uyarı: Gerekli alan standart tabloların (T Orifis vb.) üzerindedir.\nÇoklu vana kullanımı değerlendirilmelidir.\n")
                 
            self.results_text.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Hata", f"Hesaplama hatası:\n{str(e)}")
            self.results_text.config(state=tk.NORMAL)
            self.results_text.insert(tk.END, f"\nHATA: {e}")
            self.results_text.config(state=tk.DISABLED)


    def create_gas_settings(self, frame):
        # Top part: Search and Listbox
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(search_frame, text="Gaz Ara:").pack(side="left")
        self.gas_search_entry = ttk.Entry(search_frame)
        self.gas_search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.gas_search_entry.bind("<KeyRelease>", self.filter_gas_list)
        
        self.gas_listbox = tk.Listbox(frame, height=5)
        self.gas_listbox.pack(fill="x", padx=5, pady=2)
        for g in self.available_gases: self.gas_listbox.insert(tk.END, g)
        
        # Middle part: Add controls
        add_frame = ttk.Frame(frame)
        add_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(add_frame, text="Mole %:").pack(side="left")
        self.mole_entry = ttk.Entry(add_frame, width=8)
        self.mole_entry.pack(side="left", padx=5)
        ttk.Button(add_frame, text="Ekle", command=self.add_gas).pack(side="left", padx=2)
        ttk.Button(add_frame, text="Temizle", command=self.clear_comp).pack(side="left", padx=2)
        
        # Bottom part: Current Composition Display
        self.comp_text = tk.Text(frame, height=5, state=tk.DISABLED, bg="#fdfdfd", font=("Arial", 9))
        self.comp_text.pack(fill="x", padx=5, pady=5)
        
    def filter_gas_list(self, event=None):
        search_term = self.gas_search_entry.get().lower()
        self.gas_listbox.delete(0, tk.END)
        for g in self.available_gases:
            if search_term in g.lower():
                self.gas_listbox.insert(tk.END, g)

    def add_gas(self):
        selected = self.gas_listbox.curselection()
        if not selected: return
        
        gas = self.gas_listbox.get(selected[0])
        frac_str = self.mole_entry.get().strip()
        
        try:
            frac = float(frac_str)
            if frac <= 0: return
            self.composition[gas] = frac
            self.update_composition_display()
            self.mole_entry.delete(0, tk.END)
        except ValueError:
            messagebox.showwarning("Geçersiz Giriş", "Lütfen geçerli bir mole yüzdesi girin.")

    def clear_comp(self):
        self.composition = {}
        self.update_composition_display()

    def update_composition_display(self):
        self.comp_text.config(state=tk.NORMAL)
        self.comp_text.delete("1.0", tk.END)
        total = sum(self.composition.values())
        if total > 0:
            for g, f in self.composition.items():
                self.comp_text.insert(tk.END, f"{g}: {f:.2f}%\n")
            self.comp_text.insert(tk.END, f"----------\nTOPLAM: {total:.2f}%")
            if abs(total - 100.0) > 0.01:
                self.comp_text.insert(tk.END, " (Normalleşecek)", "WARNING")
                self.comp_text.tag_config("WARNING", foreground="orange")
        self.comp_text.config(state=tk.DISABLED)

    def abort_simulation(self):
        self.abort_flag.set()

    def get_inputs_from_ui(self):
        inputs = {'composition': self.composition}
        if not inputs['composition']: raise ValueError("Lütfen en az 1 gaz ekleyin.")
        
        # Normalize composition to 100%
        total_pct = sum(self.composition.values())
        inputs['composition'] = {k: v/total_pct for k,v in self.composition.items()}

        def get_val(key):
            val = self.entries[key].get().strip()
            return float(val) if val else None

        def get_unit(key):
            return self.unit_combos[key].get()
        
        inputs['valve_type'] = self.valve_type_combo.get()
        
        d_val = get_val("İç Çap")
        l_val = get_val("Uzunluk")
        t_val = get_val("Et Kalınlığı")
        vol_val = get_val("Toplam Hacim")
        
        # Logic for Manual vs Geometric entry
        if vol_val is not None and (d_val is None or l_val is None):
            # Manual Mode
            inputs['V_sys'] = self.converter.convert_volume(vol_val, get_unit("Toplam Hacim"))
            inputs['HT_enabled'] = False
            self.ht_enabled_var.set(False)
            messagebox.showwarning("Analiz Uyarısı", "Toplam hacim manuel girildiği için API 521 ısıl analizi (metal-gaz ısı transferi) devre dışı bırakılmıştır. Simülasyon adyabatik olarak gerçekleştirilecektir.")
            # Dummy values for heat transfer
            inputs['A_inner'] = 1.0
            inputs['M_steel'] = 100.0
        else:
            # Geometric Mode
            if d_val is None or l_val is None or t_val is None:
                raise ValueError("Geometrik hesaplama için İç Çap, Uzunluk ve Et Kalınlığı zorunludur. Ya da sadece 'Toplam Hacim' giriniz.")
            
            D_in_m = self.converter.convert_length(d_val, get_unit("İç Çap"))
            L_m = self.converter.convert_length(l_val, get_unit("Uzunluk"))
            t_m = self.converter.convert_length(t_val, get_unit("Et Kalınlığı"))
            
            inputs['V_sys'] = math.pi * ((D_in_m/2)**2) * L_m
            inputs['A_inner'] = math.pi * D_in_m * L_m
            
            # Calculate Mass of steel
            D_out_m = D_in_m + 2*t_m
            v_outer = math.pi * ((D_out_m/2)**2) * L_m
            v_metal = v_outer - inputs['V_sys']
            inputs['M_steel'] = v_metal * 7850.0  # kg
            inputs['HT_enabled'] = self.ht_enabled_var.get()

        p0_val = get_val("Başlangıç Basıncı")
        T0_val = get_val("Başlangıç Sıcaklığı")
        pt_val = get_val("Hedef Blowdown Basıncı")
        tt_val = get_val("Hedef Blowdown Süresi")
        
        if p0_val is None or T0_val is None or pt_val is None or tt_val is None:
            raise ValueError("Basınç, Sıcaklık ve Süre alanları zorunludur.")
            
        inputs['p0_pa'] = self.converter.convert_pressure(p0_val, get_unit("Başlangıç Basıncı"))
        inputs['T0_k'] = self.converter.convert_temperature(T0_val, get_unit("Başlangıç Sıcaklığı"))
        
        inputs['p_target_blowdown_pa'] = self.converter.convert_pressure(pt_val, get_unit("Hedef Blowdown Basıncı"))
        inputs['t_target_sec'] = tt_val
        
        if inputs['p_target_blowdown_pa'] >= inputs['p0_pa']:
             raise ValueError("Hedef Basınç, Başlangıçtan küçük olmalı.")
             
        v_count_val = get_val("Vana Sayısı")
        inputs['valve_count'] = int(v_count_val) if v_count_val else 1
        
        inputs['Cd'] = get_val("Discharge Coeff (Cd)")
        inputs['Kb'] = get_val("Backpressure Coeff (Kb)")
        
        return inputs

    def start_calculation_thread(self):
        try:
            self.user_inputs = self.get_inputs_from_ui()
            
            self.btn_run["state"] = tk.DISABLED
            self.btn_abort["state"] = tk.NORMAL
            self.abort_flag.clear()
            logging.info(f"YENİ ANALİZ BAŞLATILDI: Vana Tipi={self.user_inputs['valve_type']}, Basınç={self.user_inputs['p0_pa']/1e5:.1f} bar")
            threading.Thread(target=self.run_calculation_logic, daemon=True).start()
        except Exception as e:
            logging.error(f"Giriş Hatası: {str(e)}")
            messagebox.showerror("Hata", str(e))

    def run_calculation_logic(self):
        try:
            self.update_progress_ui(10, 100, "Giriş parametreleri doğrulanıyor...")
            logging.info("Simülasyon motoru başlatılıyor...")
            
            A_req_m2 = find_blowdown_area_v3(self.user_inputs, self.update_progress_ui, self.abort_flag)
            
            if self.abort_flag.is_set() or A_req_m2 is None:
                logging.warning("Simülasyon kullanıcı tarafından durduruldu.")
                self.update_progress_ui(0, 100, "Simülasyon durduruldu.")
                return
            
            v_count = self.user_inputs['valve_count']
            A_single_req_mm2 = (A_req_m2 / v_count) * 1e6
            
            # Select Valve based on standard
            is_psv = "API 526" in self.user_inputs['valve_type']
            valve_data = load_api526_data() if is_psv else load_api6d_data()
            
            selected_valve = next((v for v in valve_data if v.area_mm2 >= A_single_req_mm2), None)
            
            if not selected_valve:
                logging.warning("Gerekli alanı karşılayan standart vana bulunamadı. En büyük vana seçiliyor.")
                selected_valve = valve_data[-1]
                
            total_selected_area = (selected_valve.area_mm2 / 1e6) * v_count
            
            self.update_progress_ui(80, 100, "V3 Sonuç Profili İşleniyor...")
            sim_df = run_blowdown_simulation_v3(self.user_inputs, total_selected_area, self.update_progress_ui, self.abort_flag, silent=False)
            
            if sim_df is not None:
                logging.info("Analiz başarıyla tamamlandı.")
                self.update_progress_ui(100, 100, "Simülasyon başarıyla tamamlandı!")
                
                margin = ((total_selected_area / A_req_m2) - 1.0) * 100
                sim_time = sim_df['t'].iloc[-1]
                target_time = self.user_inputs['t_target_sec']
                
                verdict = "PASS" if sim_time <= target_time else "FAIL"
                operator = "<=" if sim_time <= target_time else ">"
                
                if is_psv:
                    v_label = f"{selected_valve.size_in} {selected_valve.letter} ({selected_valve.size_dn})"
                    v_type_str = "PSV/PRV Orifis"
                else:
                    v_label = f"{selected_valve.size_in} ({selected_valve.size_dn})"
                    v_type_str = "Küresel Vana (API 6D)"

                report_text = (
                    "BLOWDOWN SİMÜLASYON SONUÇLARI\n"
                    "====================================\n\n"
                    f"VANA TİPİ: {v_type_str}\n"
                    f"TOPLAM GEREKLİ ALAN: {A_req_m2:.2e} m²\n"
                    f"VANA SAYISI: {v_count}\n"
                    f"SEÇİLEN VANA: {v_label}\n"
                    f"TEK VALF ALANI: {selected_valve.area_mm2:.1f} mm²\n"
                    f"TOPLAM SEÇİLEN ALAN: {total_selected_area:.2e} m²\n"
                    f"MARJ: {margin:.1f}%\n\n"
                    f"SONUÇ: {verdict}\n"
                    f"NEDEN: Tahliye süresi ({sim_time:.1f}s) {operator} Hedef süre ({target_time}s)\n"
                )
                
                if verdict == "FAIL":
                    logging.error(f"KRİTİK: Hedef süre aşıldı! ({sim_time:.1f}s > {target_time}s)")
                
                self.after(0, self.update_results_text, report_text)
                self.after(0, self.plot_results, sim_df, self.user_inputs, selected_valve)
        except Exception as e:
            logging.exception("Hesaplama sırasında beklenmedik hata oluştu.")
            self.after(0, lambda: messagebox.showerror("Hata", f"Hesaplama hatası: {str(e)}"))
        finally:
            self.after(0, lambda: self.btn_run.config(state=tk.NORMAL))
            self.after(0, lambda: self.btn_abort.config(state=tk.DISABLED))

    def update_results_text(self, text):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert(tk.END, text)
        self.results_text.config(state=tk.DISABLED)

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
                'units': {k: v.get() for k, v in self.unit_combos.items()},
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
            for k, val in data.get('units', {}).items():
                if k in self.unit_combos:
                    self.unit_combos[k].set(str(val))
            self.composition = data.get('composition', {})
            self.update_composition_display()
            messagebox.showinfo("Başarılı", "Ayarlar yüklendi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Yükleme başarısız: {e}")

    def create_api2000_pane(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(expand=True, fill="both")
        
        ttk.Label(frame, text="API Standard 2000 (Tank Venting) Hesaplayıcı", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.api_entries = {}
        api_config = [
            ("Tank Hacmi (m3)", "7949"),
            ("Latitude (Band)", "Below 42"),
            ("Pompalama Giriş Hızı (m3/h)", "100"),
            ("Pompalama Çıkış Hızı (m3/h)", "100"),
            ("İzolasyon Faktörü (Ri)", "1.0")
        ]
        
        for i, (text, default) in enumerate(api_config):
            ttk.Label(frame, text=text + ":").grid(row=i+1, column=0, sticky="w", padx=5, pady=5)
            if "Latitude" in text:
                combo = ttk.Combobox(frame, values=["Below 42", "42-58", "Above 58"], state="readonly")
                combo.grid(row=i+1, column=1, sticky="ew", padx=5, pady=5)
                combo.set("Below 42")
                self.api_entries[text] = combo
            else:
                entry = ttk.Entry(frame)
                entry.grid(row=i+1, column=1, sticky="ew", padx=5, pady=5)
                entry.insert(0, default)
                self.api_entries[text] = entry
                
        self.api_volatile_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Akışkan Uçucu (Volatile)?", variable=self.api_volatile_var).grid(row=len(api_config)+1, column=0, columnspan=2, pady=5)
        
        ttk.Button(frame, text="API 2000 Hesabını Başlat", command=self.run_api2000_calculation).grid(row=len(api_config)+2, column=0, columnspan=2, pady=10)
        
        self.api_results_text = tk.Text(frame, height=15, width=60, font=("Consolas", 10))
        self.api_results_text.grid(row=len(api_config)+3, column=0, columnspan=2, pady=10)
        
    def run_api2000_calculation(self):
        try:
            vol = float(self.api_entries["Tank Hacmi (m3)"].get())
            lat_str = self.api_entries["Latitude (Band)"].get()
            lat = 30 if "Below" in lat_str else (50 if "42-58" in lat_str else 65)
            is_vol = self.api_volatile_var.get()
            qin = float(self.api_entries["Pompalama Giriş Hızı (m3/h)"].get())
            qout = float(self.api_entries["Pompalama Çıkış Hızı (m3/h)"].get())
            ri = float(self.api_entries["İzolasyon Faktörü (Ri)"].get())
            
            res = calculate_api2000_venting(vol, lat, is_vol, qin, qout, ri)
            
            summary = (
                "--- API 2000 TANILIK HAVALANDIRMA ANALİZİ ---\n"
                f"Kullanılan C Faktörü: {res['c_factor_used']}\n"
                f"Uçucu Akışkan: {'Evet' if is_vol else 'Hayır'}\n\n"
                f"Isıl Inbreathing (Nm3/h): {res['thermal_inbreathing']:.1f}\n"
                f"Isıl Outbreathing (Nm3/h): {res['thermal_outbreathing']:.1f}\n\n"
                f"Pompa Çıkış Bileşeni (Nm3/h): {res['pump_out_component']:.1f}\n"
                f"Pompa Giriş Bileşeni (Nm3/h): {res['pump_in_component']:.1f}\n\n"
                "TOPLAM GEREKSİNİMLER (Nm3/h):\n"
                "------------------------------------\n"
                f"VACUUM (Inbreathing): {res['total_inbreathing']:.1f} Nm3/h\n"
                f"BASINÇ (Outbreathing): {res['total_outbreathing']:.1f} Nm3/h\n"
                "------------------------------------\n"
            )
            
            self.api_results_text.delete("1.0", tk.END)
            self.api_results_text.insert(tk.END, summary)
            logging.info("API 2000 hesabı başarıyla tamamlandı.")
            
        except Exception as e:
            messagebox.showerror("Hata", f"Giriş değerlerini kontrol edin: {e}")

    def show_methodology(self):
        help_win = tk.Toplevel(self)
        help_win.title("Modelleme ve Hesaplama Metodolojisi")
        help_win.geometry("700x600")
        
        txt = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=("Arial", 10), padding=15)
        txt.pack(expand=True, fill="both")
        
        content = (
            "HESAPLAMA METODOLOJİSİ VE STANDARTLAR\n\n"
            "Bu program, basınçlı sistemlerin (boru hattı, tank, kap) güvenli tahliyesini "
            "uluslararası endüstri standartlarına (API) göre analiz eder. Temel çalışma "
            "prensipleri aşağıda özetlenmiştir:\n\n"
            
            "1. API 520 (PSV/Vana Boyutlandırma)\n"
            "------------------------------------\n"
            "Gaz tahliye debisi hesaplanırken API 520 Part I'deki kütlesel akış formülleri kullanılır.\n"
            "- Kritik Akış: Gaz hızı ses hızına (Mach 1) ulaştığında basınç oranına bakmaksızın debi sabitlenir.\n"
            "- Alt-Kritik Akış: Karşı basınç yüksek olduğunda (boru hattı çıkışı vb.) debi, basınç farkına göre düşer.\n"
            "- Faktörler: Gerçek vana verimliliği (Cd) ve karşı basınç düzeltmesi (Kb) hesaba katılır.\n\n"
            
            "2. API 521 (Depressurization / Blowdown)\n"
            "------------------------------------\n"
            "Basınçlı bir kabın acil durumda tahliyesi sırasında zaman içindeki değişimleri modeller.\n"
            "- Enerji Dengesi: 1. Termodinamik Yasa kullanılarak gazın genleşirken soğuması (Joule-Thomson etkisi) "
            "adım adım simüle edilir.\n"
            "- Isı Transferi: Gaz soğurken metal cidardan (boru duvarı) ısı çeker. Program, Grashof ve Prandtl "
            "sayılarını kullanarak serbest konveksiyon (ısı transferi) hesabını yapar.\n"
            "- MDMT Analizi: En düşük metal sıcaklığı (MDMT) belirlenir. Bu, malzemenin kırılgan hale gelip "
            "gelmeyeceğini anlamak için kritik öneme sahiptir.\n\n"
            
            "3. API 2000 (Tank Havalandırma)\n"
            "------------------------------------\n"
            "Alçak basınçlı (≤ 15 psig) depolama tanklarının 'nefes alması' için gereksinimleri hesaplar.\n"
            "- Isıl Nefes Alma: Gece soğuması (Inbreathing) veya gündüz ısınması (Outbreathing) sonucu oluşan "
            "vakum veya basınç etkisi C-Faktörü ve enlem bilgisiyle hesaplanır.\n"
            "- Pompalama Etkisi: Tanktan sıvı çekilmesi veya tanka sıvı doldurulması sırasında gaz hacmindeki "
            "hızlı değişimler kütle koruması prensibiyle eklenir.\n\n"
            
            "4. Termofiziksel Özellikler (CoolProp)\n"
            "------------------------------------\n"
            "Programdaki tüm gaz özellikleri (yoğunluk, entalpi, viskozite, Z-faktörü) 'CoolProp' kütüphanesi "
            "aracılığıyla gerçek gaz denklemleriyle çözülür. Bu sayede ideal gaz varsayımı yerine, yüksek "
            "basınçlardaki gerçek davranışlar doğru yansıtılır.\n\n"
            "DİKKAT: Bu araç bir mühendislik asistanıdır. Kritik tasarımlarda sonuçların resmi API "
            "standartlarıyla ve uzman görüşüyle teyit edilmesi tavsiye edilir."
        )
        
        txt.insert(tk.END, content)
        txt.config(state=tk.DISABLED)

if __name__ == "__main__":
    Application().mainloop()
