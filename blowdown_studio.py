import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import CoolProp.CoolProp as CP
import logging
from collections import namedtuple
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
import threading
import os
import urllib.request
import urllib.error
import webbrowser
import math
from api2000_engine import calculate_api2000_venting
from hyddown_adapter import find_hyddown_blowdown_area, run_hyddown_blowdown_simulation
from psv_preliminary import calculate_preliminary_gas_psv_area
from psv_vendor_catalog import estimate_family_kb, evaluate_vendor_models_for_gas_service

# Constants and Data Structures
R_U = 8314.462618  # Universal gas constant (J/kmol·K)
P_ATM = 101325     # Standard atmospheric pressure (Pa)
T_STD = 288.7      # Standard temperature (288.7 K = 60°F)
APP_NAME = "Blowdown Studio"
APP_VERSION = "v2.3.1"
NATIVE_ENGINE_NAME = "Yerel Çözücü"

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
# NATIVE BLOWDOWN ENGINE
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
        h_inner = Nu * cond / L_char
        # Cap abnormal values
        return min(max(h_inner, 2.0), 300.0)
    except Exception as e:
        return 10.0 # Safe fallback

def parse_outlet_diameter_mm(size_dn_str):
    try:
        first_option = size_dn_str.split('/')[0].strip()
        outlet_part = first_option.split('x')[-1].strip()
        dn_val = ''.join(filter(str.isdigit, outlet_part))
        return float(dn_val)
    except:
        return 50.0 # fallback

def calculate_reaction_force(W_kg_s, T1_k, p1_pa, A_orifice_m2, k, MW_kg_kmol):
    # API 520 Part II Method for Gas
    R_spec = R_U / MW_kg_kmol
    P_throat = p1_pa * ((2 / (k + 1))**(k / (k - 1)))
    T_throat = T1_k * (2 / (k + 1))
    v_throat = math.sqrt(k * R_spec * T_throat)
    if P_throat < P_ATM: P_throat = P_ATM
    F_newtons = W_kg_s * v_throat + (P_throat - P_ATM) * A_orifice_m2
    return F_newtons

def update_state_from_rho_u_gas(state, rho_kg_m3, u_target_j_kg, t_guess_k):
    """
    CoolProp does not support Dmass-Umass flashes for mixtures.
    Solve the gas state via a bounded rho-T search against target umass.
    """
    rho_kg_m3 = max(rho_kg_m3, 1e-9)
    t_guess_k = max(t_guess_k, 80.0)
    state.specify_phase(CP.iphase_gas)

    def eval_u(temp_k):
        state.update(CP.DmassT_INPUTS, rho_kg_m3, temp_k)
        return state.umass()

    t_low = max(80.0, min(t_guess_k * 0.5, t_guess_k - 100.0))
    t_high = max(350.0, t_guess_k + 100.0, t_guess_k * 1.5)

    u_low = eval_u(t_low)
    u_high = eval_u(t_high)

    for _ in range(25):
        if u_low <= u_target_j_kg <= u_high:
            break
        if u_target_j_kg < u_low:
            next_low = max(60.0, t_low * 0.8)
            if next_low == t_low:
                break
            t_low = next_low
            u_low = eval_u(t_low)
        else:
            t_high *= 1.2
            u_high = eval_u(t_high)
    else:
        raise ValueError("Unable to bracket rho-u gas state for blowdown step.")

    if not (u_low <= u_target_j_kg <= u_high):
        raise ValueError("Unable to bracket rho-u gas state for blowdown step.")

    for _ in range(60):
        t_mid = 0.5 * (t_low + t_high)
        u_mid = eval_u(t_mid)
        if abs(u_mid - u_target_j_kg) <= 1e-6 * max(1.0, abs(u_target_j_kg)):
            break
        if u_mid < u_target_j_kg:
            t_low = t_mid
        else:
            t_high = t_mid

    state.update(CP.DmassT_INPUTS, rho_kg_m3, 0.5 * (t_low + t_high))
    return state

def find_psv_area_by_flow_rate(inputs):

    """
    Directly calculates required orifice area using API 520 mass flow equation.
    inputs requires: 'W_req_kg_h', 'p0_pa', 'T0_k', 'composition', 'Cd', 'Kb'
    """
    W_kg_s = inputs['W_req_kg_h'] / 3600.0
    p_sys = inputs['p0_pa']
    T_sys = inputs['T0_k']
    comp = inputs['composition']
    p_downstream = inputs.get('p_downstream', P_ATM)
    
    state = CP.AbstractState("HEOS", "&".join(comp.keys()))
    state.set_mole_fractions(list(comp.values()))
    state.specify_phase(CP.iphase_gas)
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
        
    return A_req_m2, is_choked, k, MW, state.hmass(), Z, pr_crit, state.rhomass()

def run_native_blowdown_simulation(inputs, vana_alani_m2, progress_callback=None, abort_flag=None, silent=False):
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
    
    p_downstream = inputs.get('p_downstream', P_ATM)
    zaman_serisi = []
    
    state = CP.AbstractState("HEOS", "&".join(comp.keys()))
    state.set_mole_fractions(list(comp.values()))
    state.specify_phase(CP.iphase_gas)
    state.update(CP.PT_INPUTS, p_sys, T_sys)
    
    U_mass = state.umass()
    MW = state.molar_mass() * 1000
    m_fluid = state.rhomass() * V_sys
    
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
            update_state_from_rho_u_gas(state, m_fluid / V_sys, U_mass, T_sys)
            p_sys = state.p()
            T_sys = state.T()
            k = state.cpmass() / state.cvmass()
            Z = state.compressibility_factor()
            H_mass = state.hmass()
        except Exception as exc:
            raise RuntimeError(f"Blowdown state update failed at t={t:.2f}s") from exc
            
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
        
        zaman_serisi.append({
            't': t, 'p_sys': p_sys, 'mdot_kg_s': dm_kg_s,
            'T_sys': T_sys, 'T_wall': T_wall, 'h_in': h_in,
            'rho_g': state.rhomass(), 'm_sys': m_fluid
        })

        t += dt
        if not silent and progress_callback and int(t/max(0.001, dt)) % 20 == 0:
            progress_callback(t, target_time)
            
        if t > max_t: break
            
    if silent:
        return t
    df = pd.DataFrame(zaman_serisi + [{
        't': t, 'p_sys': p_sys, 'mdot_kg_s': dm_kg_s,
        'T_sys': T_sys, 'T_wall': T_wall, 'h_in': h_in,
        'rho_g': state.rhomass(), 'm_sys': m_fluid
    }])
    df.attrs["engine"] = NATIVE_ENGINE_NAME
    df.attrs["time_to_target"] = t
    return df

def find_native_blowdown_area(inputs, progress_callback=None, abort_flag=None):
    target_time = inputs['t_target_sec']
    A_low, A_high = 1e-8, 2.0
    max_iter = 35
    
    for i in range(max_iter):
        if abort_flag and abort_flag.is_set(): return None
        if progress_callback: progress_callback(i, max_iter, text=f"Boyutlandırma Analizi ({i+1}/{max_iter})...")
        
        A_mid = (A_low + A_high) / 2.0
        sim_time = run_native_blowdown_simulation(inputs, A_mid, silent=True, abort_flag=abort_flag)
        
        if sim_time is None: return None
        if abs(sim_time - target_time) / target_time < 0.02: return A_mid
        if sim_time > target_time: A_low = A_mid
        else: A_high = A_mid
            
    return A_mid

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
        
        # Start auto-update check in background
        self.check_for_updates(manual=False)

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
        helpmenu.add_command(label="Güncellemeleri Kontrol Et...", command=lambda: self.check_for_updates(manual=True))
        menubar.add_cascade(label="Yardım", menu=helpmenu)
        
        self.config(menu=menubar)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=5, expand=True, fill="both", padx=5)
        
        self.main_tab = ttk.Frame(self.notebook)
        self.graphs_tab = ttk.Frame(self.notebook)
        self.api2000_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.main_tab, text="Blowdown Analizi")
        self.notebook.add(self.graphs_tab, text="Grafikler")
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

    def check_for_updates(self, manual=False):
        def _check():
            try:
                url = "https://api.github.com/repos/SLedgehammer-dev12/BLOW-DOWN-PSV/releases/latest"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                
                latest_version = data.get("tag_name", "")
                
                def v_val(v):
                    nums = [int(n) for n in __import__("re").findall(r"\d+", v)]
                    return nums if nums else [0]

                if latest_version and v_val(latest_version) > v_val(APP_VERSION):
                    self.after(0, self._prompt_update, latest_version, data)
                elif manual:
                    self.after(0, lambda: messagebox.showinfo("Güncelleme Kontrolü", f"Programınız şu anki en güncel sürümdedir ({APP_VERSION})."))
            except Exception as e:
                logging.error(f"Updates fetch failed: {e}")
                if manual:
                    self.after(0, lambda: messagebox.showerror("Hata", "Güncelleme sunucusuna bağlanılamadı. Lütfen internet bağlantınızı kontrol edin."))

        threading.Thread(target=_check, daemon=True).start()

    def _prompt_update(self, latest_version, release_data):
        release_page = release_data.get("html_url", "")
        ans = messagebox.askyesnocancel(
            "Yeni Sürüm Bulundu",
            f"Programın yeni bir sürümü yayımlanmış!\n"
            f"Mevcut: {APP_VERSION} -> Yeni: {latest_version}\n\n"
            "Evet: Varsayılan İndirilenler klasörüne indir\n"
            "Hayır: Kayıt konumunu sen seç\n"
            "İptal: İndirmeden çık"
        )
        if ans is None:
            return
        save_path = self._choose_update_download_path(release_data) if ans is False else self._default_update_download_path(release_data)
        if not save_path:
            return
        self._start_update_download(release_data, save_path, release_page)

    def _select_release_asset(self, release_data):
        assets = release_data.get("assets", [])
        if not assets:
            return None
        exe_assets = [a for a in assets if a.get("name", "").lower().endswith(".exe")]
        if not exe_assets:
            return assets[0]

        preferred_keywords = (
            "blowdown studio",
            "blowdown_studio",
            "blow down psv",
            "blow_down_psv",
        )
        for keyword in preferred_keywords:
            matched = next((a for a in exe_assets if keyword in a.get("name", "").lower()), None)
            if matched:
                return matched
        return exe_assets[0]

    def _default_update_download_path(self, release_data):
        asset = self._select_release_asset(release_data)
        if not asset:
            return None
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        return os.path.join(downloads_dir, asset.get("name", f"update_{release_data.get('tag_name', 'latest')}"))

    def _choose_update_download_path(self, release_data):
        asset = self._select_release_asset(release_data)
        if not asset:
            messagebox.showwarning("Güncelleme", "İndirilebilir dosya bulunamadı.")
            return None
        initial_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        return filedialog.asksaveasfilename(
            title="Güncelleme Dosyasını Kaydet",
            initialdir=initial_dir,
            initialfile=asset.get("name", ""),
            defaultextension=os.path.splitext(asset.get("name", ""))[1] or ".exe",
            filetypes=[("Yürütülebilir Dosya", "*.exe"), ("Tüm Dosyalar", "*.*")]
        )

    def _start_update_download(self, release_data, save_path, release_page=""):
        asset = self._select_release_asset(release_data)
        if not asset:
            messagebox.showwarning("Güncelleme", "İndirilebilir dosya bulunamadı.")
            if release_page:
                webbrowser.open(release_page)
            return

        download_url = asset.get("browser_download_url")
        if not download_url:
            messagebox.showwarning("Güncelleme", "İndirme bağlantısı bulunamadı.")
            if release_page:
                webbrowser.open(release_page)
            return

        def _download():
            try:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(save_path, "wb") as out_file:
                    total_size = int(response.headers.get("Content-Length", "0") or 0)
                    downloaded = 0
                    chunk_size = 1024 * 256
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = downloaded / total_size * 100.0
                            self.after(0, lambda p=pct: self.progress_label.config(text=f"Güncelleme indiriliyor... %{p:.1f}"))
                logging.info(f"Güncelleme dosyası indirildi: {save_path}")
                self.after(0, lambda: messagebox.showinfo("Güncelleme", f"Yeni sürüm indirildi:\n{save_path}"))
                self.after(0, lambda: self.progress_label.config(text="Güncelleme indirildi."))
            except Exception as e:
                logging.error(f"Update download failed: {e}")
                self.after(0, lambda: messagebox.showerror("Güncelleme", f"Güncelleme indirilemedi:\n{e}"))
                self.after(0, lambda: self.progress_label.config(text="Güncelleme indirilemedi."))

        self.progress_label.config(text="Güncelleme indiriliyor...")
        threading.Thread(target=_download, daemon=True).start()
            
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
        parent.rowconfigure(0, weight=1)

        # Results Text (Expanded)
        self.results_text = tk.Text(parent, bg="#f0f0f0", font=("Consolas", 11))
        self.results_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.results_text.config(state=tk.DISABLED)

        # Graphs in Graphs Tab
        self.graphs_tab.columnconfigure(0, weight=1)
        self.graphs_tab.rowconfigure(0, weight=1)
        self.fig = plt.Figure(figsize=(7.5, 8.5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graphs_tab)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self._show_graph_placeholder("Blowdown")

    def _show_graph_placeholder(self, mode_text):
        self.fig.clf()
        ax = self.fig.add_subplot(1, 1, 1)
        label = (
            "PSV ön boyutlandırma tamamlandığında grafikler burada görünecek."
            if "PSV" in mode_text
            else "Blowdown simülasyonu tamamlandığında grafikler burada görünecek."
        )
        ax.text(0.5, 0.5, label, ha="center", va="center", transform=ax.transAxes, fontsize=12)
        ax.set_axis_off()
        self.fig.tight_layout()
        self.canvas.draw()

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
            ("Backpressure (Karşı Basınç)", "barg", ["barg", "bara", "psi", "psig", "atm"]),
            ("Backpressure Coeff (Kb)", "", [""])
        ]
        
        inputs_config.insert(6, ("MAWP / Dizayn Basıncı", "barg", ["barg", "bara", "psi", "psig", "atm", "Pa", "kPa", "MPa"]))
        inputs_config.insert(7, ("Allowable Overpressure (%)", "%", ["%"]))

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
            if text == "Backpressure (Karşı Basınç)": entry.insert(0, "0")
            if text == "Allowable Overpressure (%)": entry.insert(0, "10")
            self.entries[text] = entry
            
            combo = ttk.Combobox(entry_frame, values=units, state="readonly", width=8)
            combo.grid(row=0, column=1, padx=(5, 0))
            combo.set(default_unit)
            self.unit_combos[text] = combo
            
            self.entry_frames[text] = (lbl, entry_frame)

        self.engine_options_frame = ttk.LabelFrame(frame, text="Çözüm Motoru")
        self.engine_options_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.engine_options_frame.columnconfigure(1, weight=1)
        ttk.Label(self.engine_options_frame, text="Blowdown Motoru:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.engine_combo = ttk.Combobox(self.engine_options_frame, values=[NATIVE_ENGINE_NAME, "HydDown"], state="readonly")
        self.engine_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.engine_combo.set(NATIVE_ENGINE_NAME)

        self.psv_options_frame = ttk.LabelFrame(frame, text="PSV Ön Boyutlandırma Ayarları")
        self.psv_options_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.psv_options_frame.columnconfigure(1, weight=1)
        self.psv_options_frame.columnconfigure(3, weight=1)

        ttk.Label(self.psv_options_frame, text="PRV Tasarım Tipi:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.prv_design_combo = ttk.Combobox(
            self.psv_options_frame,
            values=["Conventional", "Balanced Bellows", "Balanced Spring", "Pilot-Operated"],
            state="readonly",
        )
        self.prv_design_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.prv_design_combo.set("Conventional")

        ttk.Label(self.psv_options_frame, text="Upstream Rupture Disk:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.rupture_disk_combo = ttk.Combobox(self.psv_options_frame, values=["No", "Yes"], state="readonly")
        self.rupture_disk_combo.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.rupture_disk_combo.set("No")

        self.ht_enabled_var = tk.BooleanVar(value=True)
        self.ht_check = ttk.Checkbutton(frame, text="Isıl Analiz (Heat Transfer) Aktif", variable=self.ht_enabled_var)
        self.ht_check.grid(row=5, column=0, columnspan=2, pady=5, sticky="w", padx=5)

        self.btn_run = ttk.Button(frame, text=f"{APP_VERSION} Analizini Başlat (Enerji Balansı + MDMT)", command=self.handle_run_button)
        self.btn_run.grid(row=6, column=0, columnspan=2, pady=10, sticky="ew")
        
        self.btn_abort = ttk.Button(frame, text="Durdur", state=tk.DISABLED, command=self.abort_simulation)
        self.btn_abort.grid(row=7, column=0, columnspan=2, pady=5, sticky="ew")
        
        self.progress_label = ttk.Label(frame, text="")
        self.progress_label.grid(row=8, column=0, columnspan=2)
        
        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        self.progress.grid(row=9, column=0, columnspan=2, pady=5, sticky="ew")
        
        # Initial UI setup
        self.on_mode_change()

    def _set_field_label(self, field_name, label_text):
        self.entry_frames[field_name][0].config(text=label_text)

    def on_mode_change(self, event=None):
        mode = self.mode_combo.get()
        if "Blowdown" in mode:
            for field in ["İç Çap", "Uzunluk", "Et Kalınlığı", "Toplam Hacim", "Hedef Blowdown Süresi", "Hedef Blowdown Basıncı"]:
                self.entry_frames[field][0].grid()
                self.entry_frames[field][1].grid()
            self.entry_frames["Gerekli Tahliye Debisi"][0].grid_remove()
            self.entry_frames["Gerekli Tahliye Debisi"][1].grid_remove()
            self.entry_frames["MAWP / Dizayn Basıncı"][0].grid_remove()
            self.entry_frames["MAWP / Dizayn Basıncı"][1].grid_remove()
            self.entry_frames["Allowable Overpressure (%)"][0].grid_remove()
            self.entry_frames["Allowable Overpressure (%)"][1].grid_remove()
            self.sys_type_combo.grid()
            self.sys_type_lbl.grid()
            self.engine_options_frame.grid()
            self.psv_options_frame.grid_remove()
            self.ht_check.grid()
            self.entry_frames["Backpressure (Karşı Basınç)"][0].grid()
            self.entry_frames["Backpressure (Karşı Basınç)"][1].grid()
            self.entry_frames["Backpressure Coeff (Kb)"][0].grid()
            self.entry_frames["Backpressure Coeff (Kb)"][1].grid()
            self._set_field_label("Başlangıç Basıncı", "Başlangıç Basıncı:")
            self._set_field_label("Başlangıç Sıcaklığı", "Başlangıç Sıcaklığı:")
            self._set_field_label("Backpressure (Karşı Basınç)", "Downstream / Karşı Basınç:")
            self._set_field_label("Backpressure Coeff (Kb)", "Backpressure Faktörü (Kb):")
            self.btn_run.config(text=f"{APP_VERSION} Analizini Başlat (Enerji Balansı + MDMT)")
            self.btn_abort.grid()
            self.progress.grid()
            self.progress_label.grid()
            self._show_graph_placeholder("Blowdown")
        else:
            for field in ["İç Çap", "Uzunluk", "Et Kalınlığı", "Toplam Hacim", "Hedef Blowdown Süresi", "Hedef Blowdown Basıncı"]:
                self.entry_frames[field][0].grid_remove()
                self.entry_frames[field][1].grid_remove()
            self.entry_frames["Gerekli Tahliye Debisi"][0].grid()
            self.entry_frames["Gerekli Tahliye Debisi"][1].grid()
            self.entry_frames["MAWP / Dizayn Basıncı"][0].grid()
            self.entry_frames["MAWP / Dizayn Basıncı"][1].grid()
            self.entry_frames["Allowable Overpressure (%)"][0].grid()
            self.entry_frames["Allowable Overpressure (%)"][1].grid()
            self.sys_type_combo.grid_remove()
            self.sys_type_lbl.grid_remove()
            self.engine_options_frame.grid_remove()
            self.psv_options_frame.grid()
            self.ht_check.grid_remove()
            self.entry_frames["Backpressure (Karşı Basınç)"][0].grid()
            self.entry_frames["Backpressure (Karşı Basınç)"][1].grid()
            self.entry_frames["Backpressure Coeff (Kb)"][0].grid()
            self.entry_frames["Backpressure Coeff (Kb)"][1].grid()
            self._set_field_label("Başlangıç Basıncı", "Set Pressure:")
            self._set_field_label("Başlangıç Sıcaklığı", "Relieving Temperature:")
            self._set_field_label("Backpressure (Karşı Basınç)", "Toplam Backpressure:")
            self._set_field_label("Backpressure Coeff (Kb)", "Balanced Valve Kb:")
            self.btn_run.config(text="PSV Ön Boyutlandırmayı Hesapla (API 520-1)")
            self.btn_abort.grid_remove()
            self.progress.grid_remove()
            self.progress_label.grid_remove()
            self._show_graph_placeholder("PSV")

    def handle_run_button(self):
        mode = self.mode_combo.get()
        if "Blowdown" in mode:
            self.start_calculation_thread()
        else:
            self.run_psv_sizing()

    def _select_standard_valve(self, valve_type, area_required_mm2):
        valve_data = load_api526_data() if "API 526" in valve_type else load_api6d_data()
        selected_valve = next((item for item in valve_data if item.area_mm2 >= area_required_mm2), None)
        return selected_valve, valve_data

    def run_psv_sizing(self):
        try:
            self.update_results_text("Hesaplanıyor... Lütfen bekleyin.\n")
            self.update_idletasks()

            inputs = {'composition': self.composition}
            if not inputs['composition']:
                raise ValueError("Lütfen en az 1 gaz ekleyin.")
            
            total_pct = sum(self.composition.values())
            inputs['composition'] = {k: v/total_pct for k,v in self.composition.items()}

            def get_val(key):
                val = self.entries[key].get().strip()
                return float(val) if val else None

            def get_unit(key):
                return self.unit_combos[key].get()

            flow_val = get_val("Gerekli Tahliye Debisi")
            set_pressure_val = get_val("Başlangıç Basıncı")
            mawp_val = get_val("MAWP / Dizayn Basıncı")
            overpressure_val = get_val("Allowable Overpressure (%)")
            relieving_temp_val = get_val("Başlangıç Sıcaklığı")
            backpressure_val = get_val("Backpressure (Karşı Basınç)")
            valve_count = int(get_val("Vana Sayısı") or 1)
            
            if valve_count < 1:
                raise ValueError("Vana sayısı en az 1 olmalıdır.")
            if flow_val is None or set_pressure_val is None or relieving_temp_val is None or backpressure_val is None:
                raise ValueError("Debi, set pressure, relieving temperature ve backpressure alanları zorunludur.")

            inputs['W_req_kg_h'] = self.converter.convert_flow_rate_to_kg_h(flow_val, get_unit("Gerekli Tahliye Debisi"), inputs['composition'])
            inputs['set_pressure_pa'] = self.converter.convert_pressure(set_pressure_val, get_unit("Başlangıç Basıncı"))
            inputs['mawp_pa'] = self.converter.convert_pressure(mawp_val, get_unit("MAWP / Dizayn Basıncı")) if mawp_val is not None else inputs['set_pressure_pa']
            inputs['overpressure_pct'] = overpressure_val if overpressure_val is not None else 10.0
            inputs['relieving_temperature_k'] = self.converter.convert_temperature(relieving_temp_val, get_unit("Başlangıç Sıcaklığı"))
            inputs['p_total_backpressure_pa'] = self.converter.convert_pressure(backpressure_val, get_unit("Backpressure (Karşı Basınç)"))
            inputs['Kd'] = get_val("Discharge Coeff (Cd)") or 0.975
            inputs['Kb'] = get_val("Backpressure Coeff (Kb)")
            inputs['Kc'] = 0.9 if self.rupture_disk_combo.get() == "Yes" else 1.0
            inputs['prv_design'] = self.prv_design_combo.get()
            inputs['valve_count'] = valve_count

            valve_type = self.valve_type_combo.get()
            preliminary_kb_source = "N/A"
            preliminary_extra_warnings = []
            family_kb = None
            if "API 526" in valve_type and inputs['prv_design'] == "Balanced Bellows":
                set_pressure_gauge_pa = max(inputs['set_pressure_pa'] - P_ATM, 0.0)
                backpressure_gauge_pa = max(inputs['p_total_backpressure_pa'] - P_ATM, 0.0)
                backpressure_pct_of_set = 0.0 if set_pressure_gauge_pa <= 0.0 else (backpressure_gauge_pa / set_pressure_gauge_pa) * 100.0
                family_kb, preliminary_kb_source, family_warnings = estimate_family_kb(inputs['prv_design'], backpressure_pct_of_set)
                preliminary_extra_warnings.extend(family_warnings)
                if inputs['Kb'] is None and family_kb is not None:
                    inputs['Kb'] = family_kb
                elif inputs['Kb'] is not None:
                    preliminary_kb_source = "Manual user input"

            sizing = calculate_preliminary_gas_psv_area(inputs)
            A_req_m2 = sizing.A_req_m2
            A_req_mm2 = sizing.A_req_mm2
            rho_g = sizing.rho_relieving_kg_m3 or 0.0
            V_req_m3_h = (inputs['W_req_kg_h'] / rho_g) if rho_g > 0.0 else None

            A_req_per_valve_m2 = A_req_m2 / valve_count
            A_req_per_valve_mm2 = A_req_mm2 / valve_count

            vendor_evaluation = None
            vendor_selection = None
            selected_valve, valve_data = self._select_standard_valve(valve_type, A_req_per_valve_mm2)
            pipe_d_mm = 50.0
            actual_area_m2 = A_req_per_valve_m2
            if "API 526" in valve_type:
                vendor_evaluation = evaluate_vendor_models_for_gas_service(
                    sizing=sizing,
                    required_flow_kg_h=inputs['W_req_kg_h'],
                    valve_count=valve_count,
                    valve_design=inputs['prv_design'],
                    Kc=sizing.Kc,
                )
                vendor_selection = vendor_evaluation.selected
                if vendor_selection is not None:
                    pipe_d_mm = parse_outlet_diameter_mm(vendor_selection.model.inlet_outlet_size_dn)
                    actual_area_m2 = vendor_selection.model.actual_area_mm2 / 1e6
                elif selected_valve:
                    pipe_d_mm = parse_outlet_diameter_mm(selected_valve.size_dn)
                    actual_area_m2 = selected_valve.area_mm2 / 1e6
            elif selected_valve:
                pipe_d_mm = parse_outlet_diameter_mm(selected_valve.size_dn)
                actual_area_m2 = selected_valve.area_mm2 / 1e6

            W_kg_s_per_valve = (inputs['W_req_kg_h'] / 3600.0) / valve_count
            force_N = calculate_reaction_force(
                W_kg_s_per_valve,
                inputs['relieving_temperature_k'],
                sizing.relieving_pressure_pa,
                actual_area_m2,
                sizing.k_real,
                sizing.MW_kg_kmol,
            )
            force_kgf = force_N / 9.81

            mach_number = None
            if selected_valve and sizing.h_relieving_j_kg is not None:
                state_down = CP.AbstractState("HEOS", "&".join(inputs['composition'].keys()))
                state_down.set_mole_fractions(list(inputs['composition'].values()))
                try:
                    state_down.update(CP.HmassP_INPUTS, sizing.h_relieving_j_kg, sizing.backpressure_pa)
                    rho_down = state_down.rhomass()
                    c_down = state_down.speed_sound()
                    A_pipe_m2 = math.pi * ((pipe_d_mm / 1000.0) / 2.0) ** 2
                    v_down = W_kg_s_per_valve / max(rho_down * A_pipe_m2, 1e-12)
                    mach_number = v_down / c_down
                except Exception:
                    mach_number = None

            warning_lines = list(sizing.warnings)
            warning_lines.extend(preliminary_extra_warnings)
            if sizing.backpressure_pct_of_set > 10.0 and inputs['prv_design'] == "Conventional":
                warning_lines.append(
                    "Conventional PRV için total backpressure, set pressure'ın %10 screening seviyesini aşıyor. API 520-1 ve üretici limiti ayrıca doğrulanmalıdır."
                )
            if inputs['prv_design'] != "Balanced Bellows" and get_val("Backpressure Coeff (Kb)") is not None:
                warning_lines.append(
                    f"{inputs['prv_design']} için manuel Kb girdisi ön boyutlandırmada kullanılmadı."
                )
            if (
                inputs['prv_design'] == "Balanced Bellows"
                and inputs['Kb'] is not None
                and family_kb is not None
                and abs(float(inputs['Kb']) - family_kb) > 0.01
            ):
                warning_lines.append(
                    f"Kullanıcı Kb={float(inputs['Kb']):.3f}; built-in vendor eğrisi aynı backpressure için Kb={family_kb:.3f} veriyor."
                )
            if "API 526" not in valve_type:
                warning_lines.append(
                    "API 6D sonucu yalnız nominal geçiş alanı karşılaştırmasıdır; ASME/API sertifikalı PSV kapasite seçimi yerine kullanılamaz."
                )
            if vendor_selection is not None:
                warning_lines.extend(vendor_selection.warnings)
            elif vendor_evaluation is not None and vendor_evaluation.evaluated:
                warning_lines.append("Vendor veri modeline göre hiçbir PSV modeli aynı anda efektif alan ve certified-capacity şartını sağlamadı.")

            report_lines = [
                "API 520-1 GAZ/VAPOR PSV ÖN BOYUTLANDIRMA RAPORU",
                "================================================",
                "",
                "Bu çıktı ön boyutlandırmadır. Final PSV seçimi için actual area, certified capacity, üretici Kb eğrileri ve ASME Section XIII doğrulaması gerekir.",
                "",
                "[1] Girdi ve Relieving Koşulları",
                f"Valf standardı / kıyası       : {valve_type}",
                f"PRV tasarım tipi              : {inputs['prv_design']}",
                f"Upstream rupture disk         : {self.rupture_disk_combo.get()}",
                f"Set pressure                  : {inputs['set_pressure_pa'] / 1e5:.3f} bara",
                f"MAWP / design pressure        : {inputs['mawp_pa'] / 1e5:.3f} bara",
                f"Allowable overpressure        : %{inputs['overpressure_pct']:.1f}",
                f"Relieving pressure (P1)       : {sizing.relieving_pressure_pa / 1e5:.3f} bara",
                f"Total backpressure (P2)       : {sizing.backpressure_pa / 1e5:.3f} bara",
                f"Relieving temperature         : {inputs['relieving_temperature_k'] - 273.15:.2f} °C",
                f"Gerekli kütlesel debi (W)     : {inputs['W_req_kg_h']:,.2f} kg/h",
            ]
            if V_req_m3_h is not None:
                report_lines.append(f"Relieving hacimsel debi       : {V_req_m3_h:,.2f} m³/h")
            report_lines.extend([
                "",
                "[2] API 520-1 Ön Boyutlandırma",
                f"Akış rejimi                   : {sizing.flow_regime}",
                f"Kullanılan denklem            : {sizing.equation_id}",
                f"Kritik basınç oranı           : {sizing.critical_pressure_ratio:.4f}",
                f"Gauge backpressure / set      : %{sizing.backpressure_pct_of_set:.2f}",
                f"k ideal                       : {sizing.k_ideal:.4f}",
                f"k real                        : {sizing.k_real:.4f}",
                f"Z faktörü                     : {sizing.Z:.4f}",
                f"MW                            : {sizing.MW_kg_kmol:.3f} kg/kmol",
                f"Kd                            : {sizing.Kd:.3f}",
                f"Kc                            : {sizing.Kc:.3f}",
                f"Kb kullanılan                 : {sizing.Kb_used:.3f}",
                f"Preliminary Kb kaynağı        : {preliminary_kb_source}",
            ])
            if sizing.F2 is not None:
                report_lines.append(f"F2                            : {sizing.F2:.4f}")
            report_lines.extend([
                f"Toplam gerekli alan           : {A_req_mm2:,.2f} mm²",
                f"Vana sayısı                   : {valve_count}",
                f"Vana başına gerekli alan      : {A_req_per_valve_mm2:,.2f} mm²",
                "",
                "[3] Mekanik Screening",
                f"Açık deşarj reaksiyon kuvveti : {force_N:,.0f} N ({force_kgf:,.1f} kgf) / vana",
                "Not                           : Reaksiyon kuvveti mevcut uygulamadaki screening hesabıdır; API 520-2 tam outlet-condition yöntemi değildir.",
            ])
            if mach_number is not None:
                report_lines.append(f"Çıkış Mach screening          : {mach_number:.3f}")
                report_lines.append("Not                           : Mach kontrolü yalnız kaba screening içindir; API 521 acoustic fatigue/AIV değerlendirmesinin yerini tutmaz.")
            else:
                report_lines.append("Çıkış Mach screening          : Hesaplanamadı")

            report_lines.extend([
                "",
                "[4] Vana Seçimi",
            ])
            if "API 526" in valve_type and vendor_selection is not None:
                report_lines.extend([
                    f"Vendor katalog                : {vendor_evaluation.catalog_name if vendor_evaluation else 'N/A'}",
                    f"Üretici / seri                : {vendor_selection.model.manufacturer} / {vendor_selection.model.series}",
                    f"Model kodu                    : {vendor_selection.model.model_code}",
                    f"Seçilen size / orifis         : {vendor_selection.model.display_size}",
                    f"Giriş / çıkış bağlantısı      : {vendor_selection.model.inlet_outlet_size_in} ({vendor_selection.model.inlet_outlet_size_dn})",
                    f"Tek vana efektif alan         : {vendor_selection.model.effective_area_mm2:,.1f} mm²",
                    f"Tek vana actual area          : {vendor_selection.model.actual_area_mm2:,.1f} mm²",
                    f"Certified gas Kd              : {vendor_selection.model.certified_kd_gas:.3f}",
                    f"Certified Kb                  : {vendor_selection.kb_used:.3f} ({vendor_selection.kb_source})",
                    f"Gerekli debi / vana           : {vendor_selection.required_flow_kg_h:,.2f} kg/h",
                    f"Certified capacity / vana     : {vendor_selection.certified_capacity_kg_h:,.2f} kg/h",
                    f"Efektif alan marjı            : %{vendor_selection.effective_area_margin_pct:.1f}",
                    f"Certified capacity marjı      : %{vendor_selection.certified_capacity_margin_pct:.1f}",
                    f"Veri kaynağı                  : {vendor_selection.model.source}",
                ])
            elif "API 526" in valve_type and vendor_evaluation is not None and vendor_evaluation.evaluated:
                largest_vendor = vendor_evaluation.evaluated[-1]
                report_lines.extend([
                    f"Vendor katalog                : {vendor_evaluation.catalog_name}",
                    "Vendor seçim                  : Uygun model bulunamadı",
                    f"En büyük değerlendirilen model: {largest_vendor.model.model_code} / {largest_vendor.model.display_size}",
                    f"Efektif alan                  : {largest_vendor.model.effective_area_mm2:,.1f} mm²",
                    f"Actual area                   : {largest_vendor.model.actual_area_mm2:,.1f} mm²",
                    f"Certified capacity / vana     : {largest_vendor.certified_capacity_kg_h:,.2f} kg/h",
                ])
            elif selected_valve:
                margin_pct = ((selected_valve.area_mm2 * valve_count) - A_req_mm2) / A_req_mm2 * 100.0
                report_lines.extend([
                    f"Seçilen nominal vana          : {selected_valve.size_in} ({selected_valve.size_dn})",
                    f"Nominal geçiş alanı           : {selected_valve.area_mm2:,.1f} mm²",
                    f"Toplam alan marjı             : %{margin_pct:.1f}",
                ])
            else:
                largest_valve = valve_data[-1] if valve_data else None
                report_lines.extend([
                    "Standart seçim                : Uygun vana bulunamadı",
                    f"En büyük mevcut seçenek       : {largest_valve.size_in} ({largest_valve.size_dn}) / {largest_valve.area_mm2:,.1f} mm²" if largest_valve else "En büyük mevcut seçenek       : N/A",
                    "Öneri                         : Vana sayısını artırın veya farklı sertifikalı çözüm değerlendirin.",
                ])

            if warning_lines:
                report_lines.extend(["", "[5] Uyarılar"])
                report_lines.extend(f"- {line}" for line in warning_lines)

            self.update_results_text("\n".join(report_lines))
            self.plot_psv_graphs(
                sizing,
                inputs,
                selected_valve,
                valve_data,
                vendor_selection,
                vendor_evaluation,
                force_N,
                valve_count,
            )

        except Exception as e:
            messagebox.showerror("Hata", f"Hesaplama hatası:\n{str(e)}")
            self.update_results_text(f"HATA: {e}\n")


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
        inputs['solver_engine'] = self.engine_combo.get()
        inputs['system_type'] = self.sys_type_combo.get()

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
            inputs['D_in_m'] = D_in_m
            inputs['L_m'] = L_m
            inputs['t_m'] = t_m
            
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
        
        pb_val = get_val("Backpressure (Karşı Basınç)")
        inputs['p_downstream'] = self.converter.convert_pressure(pb_val, get_unit("Backpressure (Karşı Basınç)")) if pb_val is not None else P_ATM
        
        inputs['Cd'] = get_val("Discharge Coeff (Cd)") or 0.975
        inputs['Kb'] = get_val("Backpressure Coeff (Kb)") or 1.0

        if inputs['solver_engine'] == "HydDown" and any(key not in inputs for key in ("D_in_m", "L_m", "t_m")):
            raise ValueError("HydDown motoru için geometrik giriş zorunludur. İç çap, uzunluk ve et kalınlığını giriniz.")
        
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

            engine_name = self.user_inputs.get('solver_engine', NATIVE_ENGINE_NAME)
            if engine_name == "HydDown":
                A_req_m2 = find_hyddown_blowdown_area(self.user_inputs, self.update_progress_ui, self.abort_flag)
            else:
                A_req_m2 = find_native_blowdown_area(self.user_inputs, self.update_progress_ui, self.abort_flag)
            
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
            
            self.update_progress_ui(80, 100, f"{engine_name} sonuç profili işleniyor...")
            if engine_name == "HydDown":
                sim_df = run_hyddown_blowdown_simulation(self.user_inputs, total_selected_area, self.update_progress_ui, self.abort_flag, silent=False)
            else:
                sim_df = run_native_blowdown_simulation(self.user_inputs, total_selected_area, self.update_progress_ui, self.abort_flag, silent=False)
            
            if sim_df is not None:
                logging.info("Analiz başarıyla tamamlandı.")
                self.update_progress_ui(100, 100, "Simülasyon başarıyla tamamlandı!")
                
                margin = ((total_selected_area / A_req_m2) - 1.0) * 100
                sim_time = sim_df.attrs.get("time_to_target", sim_df['t'].iloc[-1])
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
                    f"HESAP MOTORU: {engine_name}\n"
                    f"VANA TİPİ: {v_type_str}\n"
                    f"TOPLAM GEREKLİ ALAN: {A_req_m2:.2e} m²\n"
                    f"VANA SAYISI: {v_count}\n"
                    f"SEÇİLEN VANA: {v_label}\n"
                    f"TEK VALF ALANI: {selected_valve.area_mm2:.1f} mm²\n"
                    f"TOPLAM SEÇİLEN ALAN: {total_selected_area:.2e} m²\n"
                    f"MARJ: {margin:.1f}%\n\n"
                    f"SONUÇ: {verdict}\n"
                    f"NEDEN: Hedef basınca iniş süresi ({sim_time:.1f}s) {operator} Hedef süre ({target_time}s)\n"
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
        return self.plot_blowdown_results(sim_df, inputs, valve)

    def plot_blowdown_results(self, sim_df, inputs, valve):
        self.fig.clf()
        axes = self.fig.subplots(3, 2)
        engine_name = sim_df.attrs.get("engine", NATIVE_ENGINE_NAME)

        axes[0, 0].plot(sim_df['t'], sim_df['p_sys'] / 1e5, color='blue')
        axes[0, 0].set_ylabel('Basınç (bara)')
        axes[0, 0].set_title(f"{engine_name} - Oda Basıncı Düşümü")
        axes[0, 0].grid(True)

        axes[0, 1].plot(sim_df['t'], sim_df['mdot_kg_s'] * 3600.0, color='purple')
        axes[0, 1].set_ylabel('Kütlesel Tahliye (kg/h)')
        axes[0, 1].set_title('Vana Eşzamanlı Debisi')
        axes[0, 1].grid(True)

        axes[1, 0].plot(sim_df['t'], sim_df['m_sys'], color='red')
        axes[1, 0].set_ylabel('Kalan Kütle (kg)')
        axes[1, 0].set_title('Sistem Kütle Azalışı')
        axes[1, 0].grid(True)

        rho_safe = np.maximum(np.asarray(sim_df['rho_g'], dtype=float), 1e-12)
        v_h = (np.asarray(sim_df['mdot_kg_s'], dtype=float) * 3600.0) / rho_safe
        axes[1, 1].plot(sim_df['t'], v_h, color='green')
        axes[1, 1].set_ylabel('Hacimsel Tahliye (m³/h)')
        axes[1, 1].set_title('Volümetrik Çıkış Miktarı')
        axes[1, 1].grid(True)

        axes[2, 0].plot(sim_df['t'], sim_df['T_sys'] - 273.15, label='Gaz', color='orange')
        axes[2, 0].plot(sim_df['t'], sim_df['T_wall'] - 273.15, label='Metal', color='black', alpha=0.7)
        axes[2, 0].set_ylabel('Sıcaklık (°C)')
        axes[2, 0].set_xlabel('Zaman (s)')
        axes[2, 0].set_title('Sıcaklık Dalgalanmaları')
        axes[2, 0].legend()
        axes[2, 0].grid(True)

        axes[2, 1].plot(sim_df['t'], sim_df['h_in'], color='brown')
        axes[2, 1].set_ylabel('Konveksiyon (W/m²K)')
        axes[2, 1].set_xlabel('Zaman (s)')
        axes[2, 1].set_title('İç Isı Transfer Katsayısı')
        axes[2, 1].grid(True)

        self.fig.tight_layout()
        self.canvas.draw()
        self.notebook.select(self.graphs_tab)

    def plot_psv_graphs(self, sizing, inputs, selected_valve, valve_data, vendor_selection, vendor_evaluation, force_N_design, valve_count):
        self.fig.clf()
        axes = self.fig.subplots(2, 2)
        required_area_mm2 = sizing.A_req_mm2 / max(valve_count, 1)
        flow_per_valve_kg_s = (inputs['W_req_kg_h'] / 3600.0) / max(valve_count, 1)

        ax1 = axes[0, 0]
        if "API 526" in self.valve_type_combo.get():
            letters = [o.letter for o in valve_data]
            areas = [o.area_mm2 for o in valve_data]
            colors_b = []
            selected_found = False
            for item in valve_data:
                if not selected_found and item.area_mm2 >= required_area_mm2:
                    colors_b.append('tomato')
                    selected_found = True
                elif item.area_mm2 >= required_area_mm2:
                    colors_b.append('lightcoral')
                else:
                    colors_b.append('steelblue')
            ax1.bar(letters, areas, color=colors_b, edgecolor='black', linewidth=0.5)
            ax1.axhline(required_area_mm2, color='purple', linestyle='--', linewidth=1.5, label=f'Gerekli: {required_area_mm2:.0f} mm²')
            ax1.set_xlabel('API 526 Orifis')
            ax1.set_ylabel('Efektif Alan (mm²)')
            ax1.set_title('Standart Orifis Karşılaştırması')
            ax1.legend()
            ax1.grid(axis='y')
        else:
            ax1.text(0.5, 0.5, 'API 526 grafiği bu seçim için uygulanmadı.', ha='center', va='center', transform=ax1.transAxes)
            ax1.set_axis_off()

        ax2 = axes[0, 1]
        if vendor_evaluation and vendor_evaluation.evaluated:
            display_items = vendor_evaluation.evaluated[: min(8, len(vendor_evaluation.evaluated))]
            labels = [item.model.display_size for item in display_items]
            margins = [item.certified_capacity_margin_pct for item in display_items]
            colors_b = ['seagreen' if item.meets_required_capacity and item.meets_required_effective_area else 'darkorange' for item in display_items]
            ax2.bar(range(len(display_items)), margins, color=colors_b)
            ax2.axhline(0.0, color='black', linewidth=1.0)
            ax2.set_xticks(range(len(display_items)))
            ax2.set_xticklabels(labels, rotation=35, ha='right')
            ax2.set_ylabel('Capacity Margin (%)')
            ax2.set_title('Vendor Certified Capacity Screening')
            ax2.grid(axis='y')
        else:
            ax2.text(0.5, 0.5, 'Vendor screening verisi bulunamadı.', ha='center', va='center', transform=ax2.transAxes)
            ax2.set_axis_off()

        ax3 = axes[1, 0]
        if valve_data:
            x_labels = [item.letter if hasattr(item, 'letter') else item.size_in for item in valve_data]
            forces = [
                calculate_reaction_force(
                    flow_per_valve_kg_s,
                    inputs['relieving_temperature_k'],
                    sizing.relieving_pressure_pa,
                    max(item.area_mm2, 1e-9) / 1e6,
                    sizing.k_real,
                    sizing.MW_kg_kmol,
                ) / 1000.0
                for item in valve_data
            ]
            ax3.plot(x_labels, forces, color='darkorange', marker='o', linewidth=2)
            ax3.axhline(force_N_design / 1000.0, color='red', linestyle='--', label='Seçilen vana kuvveti')
            ax3.set_ylabel('Reaksiyon Kuvveti (kN)')
            ax3.set_title('Vana Boyutuna Göre Reaksiyon Kuvveti')
            ax3.legend()
            ax3.grid(True)
        else:
            ax3.text(0.5, 0.5, 'Mekanik screening verisi yok.', ha='center', va='center', transform=ax3.transAxes)
            ax3.set_axis_off()

        ax4 = axes[1, 1]
        bp_pct_range = np.linspace(0, 50, 100)
        kb_conv = np.where(bp_pct_range <= 10, 1.0, np.maximum(0.0, 1.0 - (bp_pct_range - 10) / 40.0))
        kb_bbell = np.where(bp_pct_range <= 30, 1.0, np.maximum(0.0, 1.0 - (bp_pct_range - 30) / 20.0))
        actual_bp = sizing.backpressure_pct_of_set
        ax4.plot(bp_pct_range, kb_conv, color='steelblue', linewidth=2, label='Conventional')
        ax4.plot(bp_pct_range, kb_bbell, color='seagreen', linewidth=2, label='Balanced Bellows')
        ax4.axvline(actual_bp, color='red', linestyle='--', label=f'Mevcut BP: {actual_bp:.1f}%')
        if vendor_selection is not None:
            ax4.scatter([actual_bp], [vendor_selection.kb_used], color='black', zorder=5, label=f'Seçilen Kb: {vendor_selection.kb_used:.3f}')
        ax4.set_xlabel('Karşı Basınç / Set (%)')
        ax4.set_ylabel('Kb')
        ax4.set_ylim(0.0, 1.1)
        ax4.set_title('Backpressure Screening')
        ax4.legend()
        ax4.grid(True)

        self.fig.tight_layout()
        self.canvas.draw()
        self.notebook.select(self.graphs_tab)
        return
        engine_name = sim_df.attrs.get("engine", NATIVE_ENGINE_NAME)
        
        # Pressure
        self.ax1.plot(sim_df['t'], sim_df['p_sys'] / 1e5, color='blue')
        self.ax1.set_ylabel('Basınç (bara)'); self.ax1.grid(True)
        self.ax1.set_title(f"{engine_name} Blowdown Simülasyonu")
        
        # Temperatures
        self.ax2.plot(sim_df['t'], sim_df['T_sys'] - 273.15, label='İç Akışkan (Gaz) Sıc.', color='orange')
        self.ax2.plot(sim_df['t'], sim_df['T_wall'] - 273.15, label='Metal Duvar (MDMT)', color='red', linewidth=2)
        self.ax2.set_ylabel('Sıcaklık (°C)'); self.ax2.legend(); self.ax2.grid(True)
        
        # Convection
        self.ax3.plot(sim_df['t'], sim_df['h_in'], label='İç Konveksiyon h (W/m²K)', color='green')
        self.ax3.set_ylabel('Isı Transfer Ksh.'); self.ax3.set_xlabel('Zaman (s)'); self.ax3.grid(True)
        
        self.fig.tight_layout()
        self.canvas.draw()
        self.notebook.select(self.graphs_tab)
        return

    def save_settings(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            data = {
                'mode': self.mode_combo.get(),
                'system_type': self.sys_type_combo.get(),
                'valve_type': self.valve_type_combo.get(),
                'solver_engine': self.engine_combo.get(),
                'prv_design': self.prv_design_combo.get(),
                'rupture_disk': self.rupture_disk_combo.get(),
                'ht_enabled': self.ht_enabled_var.get(),
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
            self.mode_combo.set(data.get('mode', "Zamana Bağlı Basınç Düşürme (Blowdown)"))
            self.sys_type_combo.set(data.get('system_type', "Boru Hattı (Pipeline)"))
            self.valve_type_combo.set(data.get('valve_type', "API 526 (PSV/PRV)"))
            self.engine_combo.set(data.get('solver_engine', NATIVE_ENGINE_NAME))
            self.prv_design_combo.set(data.get('prv_design', "Conventional"))
            self.rupture_disk_combo.set(data.get('rupture_disk', "No"))
            self.ht_enabled_var.set(data.get('ht_enabled', True))
            for k, val in data.get('entries', {}).items():
                if k in self.entries:
                    self.entries[k].delete(0, tk.END)
                    self.entries[k].insert(0, str(val))
            for k, val in data.get('units', {}).items():
                if k in self.unit_combos:
                    self.unit_combos[k].set(str(val))
            self.composition = data.get('composition', {})
            self.update_composition_display()
            self.on_mode_change()
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
            "PSV modu, API 520-1'e göre gaz/vapor servisinde ön boyutlandırma yapar.\n"
            "- Set pressure, allowable overpressure ve atmosfer basıncı kullanılarak relieving pressure (P1) kurulur.\n"
            "- Kritik akışta API 520-1 Eq. (9), subkritik akışta Eq. (19) ve Eq. (22) yaklaşımı kullanılır.\n"
            "- Conventional, balanced bellows ve pilot-operated vana tipleri için backpressure mantığı ayrıştırılır.\n"
            "- API 526 seçiminde built-in vendor veri modeli ile effective area, actual area, certified gas Kd ve balanced bellows Kb eğrisi üzerinden ek bir screening yapılır.\n"
            "- Built-in katalog örnek veridir; gerçek final seçim için vendor datasheet ve ASME Section XIII doğrulaması ayrıca gerekir.\n\n"
            
            "2. API 521 (Depressurization / Blowdown)\n"
            "------------------------------------\n"
            "Blowdown modu, zaman bağlı depressuring davranışını iki alternatif motorla çözer.\n"
            f"- {NATIVE_ENGINE_NAME}, enerji dengesi ve iç ısı transferi ile tek-hacim blowdown çözümü yapar.\n"
            "- HydDown motoru, ayrı bir kütüphane üzerinden vessel/pipeline geometrisi ile transient çözüm üretir.\n"
            "- Her iki motor da hedef basınca iniş süresine göre gerekli tahliye alanını iteratif olarak bulur.\n"
            "- MDMT ve sıcaklık profilleri screening amaçlıdır; yangın, iki-faz ve dağıtılmış boru hattı transientleri için ileri doğrulama gerekebilir.\n\n"
            
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
