import sys
import os
import json
import math
import logging
from logging.handlers import RotatingFileHandler
from collections import OrderedDict
import warnings
from scipy.optimize import fsolve
import numpy as np

# PyQt5 için GUI bileşenleri
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QLabel, QLineEdit, QComboBox, QPushButton, QSpinBox,
                             QCheckBox, QTabWidget, QTextEdit, QMessageBox, QProgressBar,
                             QDoubleSpinBox, QFileDialog, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Constants
P_ATM = 101325  # Pa
GAS_CONSTANT = 8314.462618  # J/(kmol·K)
DT_INITIAL = 0.02  # s
DT_MIN = 1e-6  # s
DT_MAX = 1.0  # s
TOL_TIME = 0.5  # s
TOL_PRESSURE = 0.01  # 1%

# API 520 Orifice Areas (m²)
API_520_ORIFICE_AREAS = {
    'D': 7.1e-5, 'E': 1.03e-4, 'F': 1.41e-4, 'G': 2.01e-4,
    'H': 2.84e-4, 'J': 3.60e-4, 'K': 4.47e-4, 'L': 5.57e-4,
    'M': 6.68e-4, 'N': 7.80e-4, 'P': 9.61e-4, 'Q': 1.13e-3,
    'R': 1.32e-3, 'T': 1.67e-3, 'V': 2.45e-3
}

# ASME B36.10 Pipe Schedules (NPS, Schedule 40 inner diameters in m)
ASME_B36_10_PIPES = {
    '1/8"': 0.01021, '1/4"': 0.01339, '3/8"': 0.01707, '1/2"': 0.02210,
    '3/4"': 0.02776, '1"': 0.03505, '1 1/4"': 0.04428, '1 1/2"': 0.05250,
    '2"': 0.06271, '2 1/2"': 0.07793, '3"': 0.09076, '3 1/2"': 0.10160,
    '4"': 0.11582, '5"': 0.13970, '6"': 0.16828, '8"': 0.21908,
    '10"': 0.27305, '12"': 0.32385, '14"': 0.34925, '16"': 0.40005
}

class BlowdownSimulator:
    def __init__(self):
        self.setup_logging()
        self.gas_props_cache = {}
        
        # CoolProp gaz isimleri eşleştirmesi
        self.coolprop_gas_names = {
            'CH4': 'Methane',
            'C2H6': 'Ethane',
            'C3H8': 'Propane',
            'N2': 'Nitrogen',
            'CO2': 'CO2',
            'O2': 'Oxygen',
            'H2': 'Hydrogen',
            'H2O': 'Water',
            'AR': 'Argon',
            'HE': 'Helium'
        }
        
    def setup_logging(self):
        """Logging kurulumu"""
        self.logger = logging.getLogger('blowdown_app')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = RotatingFileHandler('blowdown_app.log', maxBytes=10485760, backupCount=5)
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def convert_to_coolprop_names(self, composition):
        """
        Kullanıcı gaz isimlerini CoolProp isimlerine dönüştürür
        """
        coolprop_comp = {}
        for gas, fraction in composition.items():
            coolprop_name = self.coolprop_gas_names.get(gas.upper(), gas)
            coolprop_comp[coolprop_name] = fraction
        return coolprop_comp
    
    def gas_props(self, T, p, composition):
        """
        Gaz özelliklerini hesaplar
        """
        # Cache key oluştur
        cache_key = (round(T, 6), round(p, 1), tuple(sorted(composition.items())))
        
        # Cache'te varsa döndür
        if cache_key in self.gas_props_cache:
            return self.gas_props_cache[cache_key]
        
        # CoolProp isimlerine dönüştür
        coolprop_comp = self.convert_to_coolprop_names(composition)
        
        try:
            # CoolProp kullanılabilirse
            import CoolProp.CoolProp as CP
            
            # Gaz karışımı string'i oluştur
            gas_mixture = '&'.join([f'{k}[{v}]' for k, v in coolprop_comp.items()])
            
            # Gaz özelliklerini hesapla
            try:
                MW = CP.PropsSI('M', 'T', T, 'P', p, gas_mixture)
                Z = CP.PropsSI('Z', 'T', T, 'P', p, gas_mixture)
                cp = CP.PropsSI('C', 'T', T, 'P', p, gas_mixture)
                cv = CP.PropsSI('O', 'T', T, 'P', p, gas_mixture)
                k = cp / cv if cv != 0 else 1.4
                R_s = GAS_CONSTANT / MW
                rho = p / (Z * R_s * T)
                a = math.sqrt(k * Z * R_s * T)
                mu = CP.PropsSI('V', 'T', T, 'P', p, gas_mixture)
                
                props = {
                    'MW': MW, 'Z': Z, 'cp': cp, 'cv': cv, 'k': k, 
                    'R_s': R_s, 'rho': rho, 'a': a, 'mu': mu
                }
                
            except Exception as e:
                self.logger.warning(f"CoolProp calculation failed: {e}, using ideal gas approximation")
                props = self.ideal_gas_props(T, p, composition)
            
        except ImportError:
            # CoolProp yoksa ideal gaz varsayımı
            self.logger.warning("CoolProp not found, using ideal gas approximation")
            props = self.ideal_gas_props(T, p, composition)
        
        except Exception as e:
            # Diğer hatalarda ideal gaz kullan
            self.logger.warning(f"CoolProp error: {e}, using ideal gas approximation")
            props = self.ideal_gas_props(T, p, composition)
        
        # Cache'e kaydet
        self.gas_props_cache[cache_key] = props
        return props
    
    def ideal_gas_props(self, T, p, composition):
        """
        Ideal gaz varsayımı ile gaz özelliklerini hesaplar
        """
        # Moleküler ağırlık hesapla
        MW = sum(composition[comp] * self.get_molecular_weight(comp) 
                for comp in composition)
        
        # Ideal gaz varsayımı
        Z = 1.0
        R_s = GAS_CONSTANT / MW
        
        # Özgül ısı oranı (k) - basit yaklaşım
        k = self.estimate_k_value(composition)
        cp = k * R_s / (k - 1) if k != 1 else 1000
        cv = R_s / (k - 1) if k != 1 else 1000
        rho = p / (R_s * T)
        a = math.sqrt(k * R_s * T)
        mu = self.sutherland_viscosity(T, composition)
        
        return {
            'MW': MW, 'Z': Z, 'cp': cp, 'cv': cv, 'k': k, 
            'R_s': R_s, 'rho': rho, 'a': a, 'mu': mu
        }
    
    def get_molecular_weight(self, gas_name):
        """Gazın moleküler ağırlığını döndürür"""
        molecular_weights = {
            'CH4': 16.04, 'C2H6': 30.07, 'C3H8': 44.10, 'N2': 28.01,
            'CO2': 44.01, 'O2': 32.00, 'H2': 2.02, 'H2O': 18.02,
            'AR': 39.95, 'HE': 4.00
        }
        return molecular_weights.get(gas_name.upper(), 29.0)
    
    def estimate_k_value(self, composition):
        """Gaz karışımı için k değerini tahmin eder"""
        k_values = {
            'CH4': 1.32, 'C2H6': 1.20, 'C3H8': 1.13, 'N2': 1.40,
            'CO2': 1.29, 'O2': 1.40, 'H2': 1.41, 'H2O': 1.33,
            'AR': 1.67, 'HE': 1.66
        }
        
        k_mix = 0
        for gas, fraction in composition.items():
            k_mix += fraction * k_values.get(gas.upper(), 1.4)
        
        return k_mix
    
    def sutherland_viscosity(self, T, composition):
        """Sutherland yasası ile viskozite hesabı"""
        sutherland_params = {
            'CH4': {'mu0': 1.10e-5, 'T0': 273, 'S': 164},
            'C2H6': {'mu0': 8.28e-6, 'T0': 273, 'S': 252},
            'N2': {'mu0': 1.66e-5, 'T0': 273, 'S': 111},
            'CO2': {'mu0': 1.37e-5, 'T0': 273, 'S': 222},
            'O2': {'mu0': 1.92e-5, 'T0': 273, 'S': 139},
            'H2': {'mu0': 8.76e-6, 'T0': 273, 'S': 72}
        }
        
        mu_mix = 0
        for i, (gas_i, frac_i) in enumerate(composition.items()):
            if gas_i.upper() not in sutherland_params:
                continue
                
            params_i = sutherland_params[gas_i.upper()]
            mu_i = params_i['mu0'] * (T / params_i['T0'])**1.5 * (params_i['T0'] + params_i['S']) / (T + params_i['S'])
            
            phi_sum = 0
            for j, (gas_j, frac_j) in enumerate(composition.items()):
                if gas_j.upper() not in sutherland_params:
                    continue
                    
                params_j = sutherland_params[gas_j.upper()]
                mu_j = params_j['mu0'] * (T / params_j['T0'])**1.5 * (params_j['T0'] + params_j['S']) / (T + params_j['S'])
                
                MW_i = self.get_molecular_weight(gas_i)
                MW_j = self.get_molecular_weight(gas_j)
                
                phi_ij = (1 + (mu_i / mu_j)**0.5 * (MW_j / MW_i)**0.25)**2 / math.sqrt(8 * (1 + MW_i / MW_j))
                phi_sum += frac_j * phi_ij
            
            mu_mix += frac_i * mu_i / phi_sum
        
        return mu_mix if mu_mix > 0 else 1.8e-5
    
    def critical_pressure_ratio(self, k):
        """Kritik basınç oranını hesaplar"""
        if abs(k - 1.0) < 1e-6:
            return 0.0
        return (2 / (k + 1)) ** (k / (k - 1))
    
    def mdot_choked(self, p_up, T_up, A, k, R_s, Z, C_d):
        """Kritik (choked) akış için kütle debisi"""
        if abs(k - 1.0) < 1e-6:
            return C_d * A * p_up * math.sqrt(1 / (R_s * T_up))
        
        term = math.sqrt(k / (Z * R_s * T_up))
        exponent = (k + 1) / (2 * (k - 1))
        critical_flow_factor = (2 / (k + 1)) ** exponent
        return C_d * A * p_up * term * critical_flow_factor
    
    def mdot_subcritical(self, p_up, p_down, T_up, A, k, R_s, Z, C_d):
        """Alt-kritik akış için kütle debisi"""
        pr = p_down / p_up
        
        if abs(k - 1.0) < 1e-6:
            return C_d * A * p_up * math.sqrt(2 * math.log(1/pr) / (R_s * T_up))
        
        term1 = math.sqrt(2 * k / ((k - 1) * Z * R_s * T_up))
        term2 = math.sqrt(pr ** (2 / k) - pr ** ((k + 1) / k))
        return C_d * A * p_up * term1 * term2
    
    def mdot_general(self, p_up, p_down, T_up, A, k, R_s, Z, C_d):
        """Genel kütle debisi hesabı"""
        if p_down >= p_up:
            return 0.0
        
        pr_crit = self.critical_pressure_ratio(k)
        
        if pr_crit == 0 or p_down / p_up <= pr_crit:
            return self.mdot_choked(p_up, T_up, A, k, R_s, Z, C_d)
        else:
            return self.mdot_subcritical(p_up, p_down, T_up, A, k, R_s, Z, C_d)
    
    def api_kb_function(self, pressure_ratio):
        """API backpressure correction factor"""
        if pressure_ratio <= 0.1:
            return 1.0
        elif pressure_ratio >= 0.5:
            return 0.6
        else:
            return 1.0 - 0.8 * (pressure_ratio - 0.1)
    
    def friction_factor_swamee_jain(self, Re, D, eps):
        """Swamee-Jain sürtünme faktörü"""
        if Re < 2300:
            return 64 / max(Re, 1e-6)
        
        term1 = eps / (3.7 * D)
        term2 = 5.74 / (max(Re, 2300) ** 0.9)
        return 0.25 / (math.log10(term1 + term2) ** 2)
    
    def compute_mdot_out_from_pipe(self, p_up, p_atm, T, D, L, eps, K_local, comp):
        """Boru içindeki akış için kütle debisi"""
        if p_up <= p_atm:
            return 0.0
        
        A = math.pi * D**2 / 4
        props = self.gas_props(T, (p_up + p_atm)/2, comp)
        rho = props['rho']
        mu = props['mu']
        
        mdot_max = self.mdot_choked(p_up, T, A, props['k'], props['R_s'], props['Z'], 1.0)
        
        def pressure_drop_eq(mdot_trial):
            if mdot_trial <= 0:
                return p_up - p_atm
            
            u = mdot_trial / (rho * A)
            Re = rho * u * D / max(mu, 1e-10)
            
            f = self.friction_factor_swamee_jain(Re, D, eps)
            delta_p = (f * L/D + K_local) * rho * u**2 / 2
            
            return delta_p - (p_up - p_atm)
        
        try:
            mdot_low = 0
            mdot_high = mdot_max
            
            for _ in range(50):
                mdot_mid = (mdot_low + mdot_high) / 2
                f_mid = pressure_drop_eq(mdot_mid)
                
                if abs(f_mid) < 1:
                    return mdot_mid
                
                if f_mid > 0:
                    mdot_high = mdot_mid
                else:
                    mdot_low = mdot_mid
            
            return (mdot_low + mdot_high) / 2
        
        except:
            return mdot_max
    
    def update_composition(self, comp_header, m_header, comp_inflow, m_inflow):
        """Header bileşimini günceller"""
        if m_header <= 0 and m_inflow <= 0:
            return comp_header
        
        total_mass = m_header + m_inflow
        new_comp = {}
        
        all_components = set(comp_header.keys()).union(comp_inflow.keys())
        
        for comp in all_components:
            mass_header = comp_header.get(comp, 0) * m_header
            mass_inflow = comp_inflow.get(comp, 0) * m_inflow
            new_comp[comp] = (mass_header + mass_inflow) / total_mass
        
        total = sum(new_comp.values())
        if abs(total - 1.0) > 1e-6:
            for comp in new_comp:
                new_comp[comp] /= total
        
        return new_comp
    
    def solve_area_for_target_time(self, params, target_time, tol=0.05):
        """Hedef süre için gerekli alanı bulur"""
        A_low = 1e-8
        A_high = (params['V_system'] / target_time) * (1 / (0.5 * params['props_sys']['a']))
        
        t_low = self.simulate_blowdown(params, A_low)['time'][-1]
        t_high = self.simulate_blowdown(params, A_high)['time'][-1]
        
        while t_high < target_time:
            A_high *= 2
            if A_high > 1:
                break
            t_high = self.simulate_blowdown(params, A_high)['time'][-1]
        
        for _ in range(20):
            A_mid = (A_low + A_high) / 2
            results = self.simulate_blowdown(params, A_mid)
            t_final = results['time'][-1]
            
            if abs(t_final - target_time) / target_time < tol:
                return A_mid
            
            if t_final < target_time:
                A_low = A_mid
                t_low = t_final
            else:
                A_high = A_mid
                t_high = t_final
        
        return (A_low + A_high) / 2
    
    def pick_diameter_or_orifice(self, A_required, N, geometry_type):
        """Uygun çap veya orifis seçer"""
        if geometry_type == "Orifice":
            areas = API_520_ORIFICE_AREAS
        else:
            areas = {size: math.pi * (diameter/2)**2 for size, diameter in ASME_B36_10_PIPES.items()}
        
        for label, A_single in sorted(areas.items(), key=lambda x: x[1]):
            if N * A_single >= A_required:
                return label, A_single
        
        largest_label = max(areas.items(), key=lambda x: x[1])[0]
        largest_area = areas[largest_label]
        return largest_label, largest_area
    
    def simulate_blowdown(self, params, A_total, dt_initial=DT_INITIAL):
        """
        Blowdown simülasyonu çalıştırır
        """
        V_system = params['V_system']
        p0_system = params['p0_system']
        T0_system = params['T0_system']
        comp_system = params['comp_system']
        valve_count = params['valve_count']
        valve_params = params.get('valve_params', {})
        heat_model = params.get('heat_model', 'adiabatic')
        n_value = params.get('n_value')
        header_present = params.get('header_present', False)
        
        if header_present:
            V_header = params['V_header']
            p_header0 = params['p_header0']
            T_header0 = params['T_header0']
            comp_header = params.get('comp_header', comp_system.copy())
            L_out = params['L_out']
            D_out = params['D_out']
            eps = params.get('eps', 4.5e-5)
            K_local = params.get('K_local', 1.0)
            header_heat = params.get('header_heat', 'isothermal')
            n_header = params.get('n_header')
        
        t = 0
        p_sys = p0_system
        T_sys = T0_system
        props_sys = self.gas_props(T_sys, p_sys, comp_system)
        m_sys = p_sys * V_system / (props_sys['Z'] * props_sys['R_s'] * T_sys)
        
        if header_present:
            props_header = self.gas_props(T_header0, p_header0, comp_header)
            m_header = p_header0 * V_header / (props_header['Z'] * props_header['R_s'] * T_header0)
            p_back = p_header0
        else:
            p_back = P_ATM
        
        A_single = A_total / valve_count
        valves = [{
            'A': A_single,
            'Kd': valve_params.get('Kd', 0.975),
            'Kb_func': valve_params.get('Kb_func', self.api_kb_function),
            'Kc': valve_params.get('Kc', 1.0)
        } for _ in range(valve_count)]
        
        results = {
            'time': [t],
            'p_sys': [p_sys],
            'p_back': [p_back],
            'mdot_in': [0],
            'mdot_out': [0],
            'vflow_actual': [0],
            'vflow_standard': [0]
        }
        
        dt = dt_initial
        max_time = 10 * params.get('target_time', 3600)
        iteration_count = 0
        
        while p_sys > P_ATM * 1.01 and t < max_time and iteration_count < 10000:
            iteration_count += 1
            
            try:
                props_sys = self.gas_props(T_sys, p_sys, comp_system)
                
                mdot_in = 0
                for valve in valves:
                    pressure_ratio = p_back / p_sys
                    Kb = valve['Kb_func'](pressure_ratio)
                    C_d = valve['Kd'] * Kb * valve['Kc']
                    mdot_valve = self.mdot_general(
                        p_sys, p_back, T_sys, valve['A'], 
                        props_sys['k'], props_sys['R_s'], props_sys['Z'], C_d
                    )
                    mdot_in += max(mdot_valve, 0)
                
                if header_present:
                    props_header = self.gas_props(T_header0, p_back, comp_header)
                    mdot_out = self.compute_mdot_out_from_pipe(
                        p_back, P_ATM, T_header0, D_out, L_out, eps, K_local, comp_header
                    )
                    
                    m_header_new = m_header + (mdot_in - mdot_out) * dt
                    m_header_min = P_ATM * V_header / (props_header['Z'] * props_header['R_s'] * T_header0)
                    m_header_new = max(m_header_new, m_header_min)
                    
                    comp_header = self.update_composition(comp_header, m_header, comp_system, mdot_in * dt)
                    
                    def residual(p_new):
                        if header_heat == 'polytropic' and n_header:
                            T_new = T_header0 * (p_new / p_back) ** ((n_header - 1) / n_header)
                        else:
                            T_new = T_header0
                        
                        props_new = self.gas_props(T_new, p_new, comp_header)
                        return m_header_new - p_new * V_header / (props_new['Z'] * props_new['R_s'] * T_new)
                    
                    try:
                        p_back_new = fsolve(residual, p_back, maxfev=100)[0]
                        p_back_new = max(p_back_new, P_ATM)
                        
                        if header_heat == 'polytropic' and n_header:
                            T_header0 = T_header0 * (p_back_new / p_back) ** ((n_header - 1) / n_header)
                        p_back = p_back_new
                    except:
                        pass
                
                else:
                    mdot_out = mdot_in
                    p_back = P_ATM
                
                m_sys_new = m_sys - mdot_in * dt
                m_sys_min = P_ATM * V_system / (props_sys['Z'] * props_sys['R_s'] * T_sys)
                m_sys_new = max(m_sys_new, m_sys_min)
                
                def residual_sys(p_new):
                    if heat_model == 'adiabatic':
                        n = props_sys['k']
                    elif heat_model == 'polytropic' and n_value:
                        n = n_value
                    else:
                        n = 1.0
                    
                    if abs(n - 1.0) < 1e-6:
                        T_new = T_sys
                    else:
                        T_new = T_sys * (p_new / p_sys) ** ((n - 1) / n)
                    
                    props_new = self.gas_props(T_new, p_new, comp_system)
                    return m_sys_new - p_new * V_system / (props_new['Z'] * props_new['R_s'] * T_new)
                
                try:
                    p_sys_new = fsolve(residual_sys, p_sys, maxfev=100)[0]
                    p_sys_new = max(p_sys_new, P_ATM)
                    
                    if heat_model == 'adiabatic':
                        n = props_sys['k']
                    elif heat_model == 'polytropic' and n_value:
                        n = n_value
                    else:
                        n = 1.0
                    
                    if abs(n - 1.0) > 1e-6:
                        T_sys = T_sys * (p_sys_new / p_sys) ** ((n - 1) / n)
                    
                    p_sys = p_sys_new
                    m_sys = m_sys_new
                    
                    if header_present:
                        m_header = m_header_new
                
                except:
                    dt /= 2
                    continue
                
                t += dt
                results['time'].append(t)
                results['p_sys'].append(p_sys)
                results['p_back'].append(p_back)
                results['mdot_in'].append(mdot_in)
                results['mdot_out'].append(mdot_out)
                
                rho_std = P_ATM / (props_sys['R_s'] * 273.15)
                results['vflow_actual'].append(mdot_in / max(props_sys['rho'], 1e-10))
                results['vflow_standard'].append(mdot_in / max(rho_std, 1e-10))
                
                pressure_change = abs(p_sys_new - results['p_sys'][-2]) / max(results['p_sys'][-2], P_ATM)
                if pressure_change < TOL_PRESSURE:
                    dt = min(dt * 1.5, DT_MAX)
                else:
                    dt = max(dt / 2, DT_MIN)
                
            except Exception as e:
                dt /= 2
                if dt < DT_MIN:
                    break
        
        return results
    
    def run_complete_analysis(self, input_params):
        """Tam analizi çalıştırır"""
        try:
            self.validate_inputs(input_params)
            
            props_sys = self.gas_props(
                input_params['T0_system'], 
                input_params['p0_system'], 
                input_params['comp_system']
            )
            input_params['props_sys'] = props_sys
            
            A_required = self.solve_area_for_target_time(
                input_params, 
                input_params['target_time']
            )
            
            label, A_single = self.pick_diameter_or_orifice(
                A_required, 
                input_params['valve_count'], 
                input_params['geometry_type']
            )
            
            A_total_selected = input_params['valve_count'] * A_single
            margin = (A_total_selected / A_required - 1) * 100
            
            results = self.simulate_blowdown(input_params, A_total_selected)
            
            report = self.generate_report(input_params, A_required, label, A_single, margin, results)
            
            return {
                'success': True,
                'A_required': A_required,
                'selected_label': label,
                'A_single': A_single,
                'A_total_selected': A_total_selected,
                'margin': margin,
                'results': results,
                'report': report
            }
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_inputs(self, params):
        """Giriş parametrelerini validate et"""
        required = ['V_system', 'p0_system', 'T0_system', 'comp_system', 'target_time', 'valve_count']
        for field in required:
            if field not in params:
                raise ValueError(f"Missing required field: {field}")
        
        if params['V_system'] <= 0:
            raise ValueError("System volume must be positive")
        
        if params['p0_system'] <= P_ATM:
            raise ValueError("System pressure must be greater than atmospheric")
        
        if params['T0_system'] <= 0:
            raise ValueError("System temperature must be positive")
        
        if params['target_time'] <= 0:
            raise ValueError("Target time must be positive")
        
        if params['valve_count'] < 1:
            raise ValueError("Valve count must be at least 1")
        
        comp_sum = sum(params['comp_system'].values())
        if abs(comp_sum - 1.0) > 1e-6:
            for comp in params['comp_system']:
                params['comp_system'][comp] /= comp_sum
        
        if params.get('heat_model') == 'polytropic':
            n = params.get('n_value')
            if n is None:
                raise ValueError("Polytropic model requires n_value")
            
            k = self.gas_props(params['T0_system'], params['p0_system'], params['comp_system'])['k']
            if n <= 1 or n > k:
                raise ValueError(f"Polytropic exponent must be 1 < n <= k (k={k:.2f})")
        
        if params.get('header_present'):
            header_fields = ['V_header', 'p_header0', 'T_header0', 'L_out', 'D_out']
            for field in header_fields:
                if field not in params:
                    raise ValueError(f"Header present but missing field: {field}")
    
    def generate_report(self, input_params, A_required, label, A_single, margin, results):
        """Rapor oluştur"""
        report = {
            'input_parameters': input_params,
            'A_required': A_required,
            'selected_label': label,
            'A_single': A_single,
            'A_total_selected': input_params['valve_count'] * A_single,
            'margin_percent': margin,
            'simulation_results': results,
            'warnings': [],
            'notes': []
        }
        
        final_time = results['time'][-1]
        target_time = input_params['target_time']
        
        if final_time <= target_time:
            report['verdict'] = 'PASS'
            report['verdict_reason'] = f'Achieved time ({final_time:.1f}s) <= target time ({target_time}s)'
        else:
            report['verdict'] = 'FAIL'
            report['verdict_reason'] = f'Achieved time ({final_time:.1f}s) > target time ({target_time}s)'
            report['recommendation'] = 'Increase valve count or select larger orifice'
        
        max_mdot = max(results['mdot_in'])
        final_mdot = results['mdot_in'][-1]
        if max_mdot > 0.9 * final_mdot:
            report['warnings'].append('Choked flow observed during initial blowdown period')
        
        if margin < 0:
            report['warnings'].append('Insufficient valve area - select larger valves or increase count')
        
        report['notes'].append(
            "This calculation uses API RP 520/521 recommended compressible flow equations. "
            "Final valve selection must be verified via vendor certified capacities and "
            "full API 520/521 procedures for special cases."
        )
        
        return report

class SimulationThread(QThread):
    """Simülasyonu thread'de çalıştırmak için"""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    
    def __init__(self, input_params):
        super().__init__()
        self.input_params = input_params
        
    def run(self):
        try:
            self.log.emit("Simülasyon başlatılıyor...")
            simulator = BlowdownSimulator()
            result = simulator.run_complete_analysis(self.input_params)
            self.finished.emit(result)
        except Exception as e:
            self.log.emit(f"Hata: {str(e)}")
            self.finished.emit({'success': False, 'error': str(e)})

class BlowdownGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.results = None
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Blowdown Simülasyon ve Valf Boyutlandırma')
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])
        main_layout.addWidget(splitter)
        
        self.create_system_group(left_layout)
        self.create_gas_composition_group(left_layout)
        self.create_valve_group(left_layout)
        self.create_thermo_group(left_layout)
        self.create_header_group(left_layout)
        
        button_layout = QHBoxLayout()
        self.run_button = QPushButton('Simülasyonu Çalıştır')
        self.run_button.clicked.connect(self.run_simulation)
        button_layout.addWidget(self.run_button)
        
        self.save_button = QPushButton('Sonuçları Kaydet')
        self.save_button.clicked.connect(self.save_results)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)
        
        left_layout.addLayout(button_layout)
        
        self.progress_bar = QProgressBar()
        left_layout.addWidget(self.progress_bar)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        left_layout.addWidget(self.log_text)
        
        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)
        
        self.results_tab = QWidget()
        self.results_layout = QVBoxLayout(self.results_tab)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_layout.addWidget(self.results_text)
        self.tabs.addTab(self.results_tab, "Sonuçlar")
        
        self.plots_tab = QWidget()
        self.plots_layout = QVBoxLayout(self.plots_tab)
        self.tabs.addTab(self.plots_tab, "Grafikler")
        
        self.load_defaults()
        
    def create_system_group(self, layout):
        group = QGroupBox("Sistem Parametreleri")
        form_layout = QVBoxLayout(group)
        
        layout1 = QHBoxLayout()
        layout1.addWidget(QLabel("Sistem Hacmi (m³):"))
        self.v_system = QDoubleSpinBox()
        self.v_system.setRange(0.1, 1000)
        self.v_system.setDecimals(3)
        layout1.addWidget(self.v_system)
        form_layout.addLayout(layout1)
        
        layout2 = QHBoxLayout()
        layout2.addWidget(QLabel("Başlangıç Basıncı (bar):"))
        self.p0_system = QDoubleSpinBox()
        self.p0_system.setRange(1, 1000)
        self.p0_system.setDecimals(1)
        layout2.addWidget(self.p0_system)
        form_layout.addLayout(layout2)
        
        layout3 = QHBoxLayout()
        layout3.addWidget(QLabel("Başlangıç Sıcaklığı (°C):"))
        self.t0_system = QDoubleSpinBox()
        self.t0_system.setRange(-50, 200)
        self.t0_system.setDecimals(1)
        layout3.addWidget(self.t0_system)
        form_layout.addLayout(layout3)
        
        layout4 = QHBoxLayout()
        layout4.addWidget(QLabel("Hedef Boşalma Süresi (s):"))
        self.target_time = QDoubleSpinBox()
        self.target_time.setRange(1, 3600)
        self.target_time.setDecimals(0)
        layout4.addWidget(self.target_time)
        form_layout.addLayout(layout4)
        
        layout.addWidget(group)
    
    def create_gas_composition_group(self, layout):
        group = QGroupBox("Gaz Bileşimi")
        form_layout = QVBoxLayout(group)
        
        layout1 = QHBoxLayout()
        layout1.addWidget(QLabel("Gaz Türü:"))
        self.gas_type = QComboBox()
        self.gas_type.addItems(["Doğal Gaz", "Özel Karışım", "Hava", "Nitrojen", "CO2"])
        self.gas_type.currentTextChanged.connect(self.on_gas_type_changed)
        layout1.addWidget(self.gas_type)
        form_layout.addLayout(layout1)
        
        self.custom_gas_group = QWidget()
        custom_layout = QVBoxLayout(self.custom_gas_group)
        
        layout2 = QHBoxLayout()
        layout2.addWidget(QLabel("CH4 (%):"))
        self.ch4_percent = QDoubleSpinBox()
        self.ch4_percent.setRange(0, 100)
        self.ch4_percent.setDecimals(2)
        layout2.addWidget(self.ch4_percent)
        custom_layout.addLayout(layout2)
        
        layout3 = QHBoxLayout()
        layout3.addWidget(QLabel("C2H6 (%):"))
        self.c2h6_percent = QDoubleSpinBox()
        self.c2h6_percent.setRange(0, 100)
        self.c2h6_percent.setDecimals(2)
        layout3.addWidget(self.c2h6_percent)
        custom_layout.addLayout(layout3)
        
        layout4 = QHBoxLayout()
        layout4.addWidget(QLabel("N2 (%):"))
        self.n2_percent = QDoubleSpinBox()
        self.n2_percent.setRange(0, 100)
        self.n2_percent.setDecimals(2)
        layout4.addWidget(self.n2_percent)
        custom_layout.addLayout(layout4)
        
        layout5 = QHBoxLayout()
        layout5.addWidget(QLabel("CO2 (%):"))
        self.co2_percent = QDoubleSpinBox()
        self.co2_percent.setRange(0, 100)
        self.co2_percent.setDecimals(2)
        layout5.addWidget(self.co2_percent)
        custom_layout.addLayout(layout5)
        
        form_layout.addWidget(self.custom_gas_group)
        self.custom_gas_group.setVisible(False)
        
        layout.addWidget(group)
    
    def create_valve_group(self, layout):
        group = QGroupBox("Valf Parametreleri")
        form_layout = QVBoxLayout(group)
        
        layout1 = QHBoxLayout()
        layout1.addWidget(QLabel("Valf Sayısı:"))
        self.valve_count = QSpinBox()
        self.valve_count.setRange(1, 10)
        layout1.addWidget(self.valve_count)
        form_layout.addLayout(layout1)
        
        layout2 = QHBoxLayout()
        layout2.addWidget(QLabel("Geometri Tipi:"))
        self.geometry_type = QComboBox()
        self.geometry_type.addItems(["Orifice", "Pipe"])
        layout2.addWidget(self.geometry_type)
        form_layout.addLayout(layout2)
        
        layout3 = QHBoxLayout()
        layout3.addWidget(QLabel("Kd Değeri:"))
        self.kd_value = QDoubleSpinBox()
        self.kd_value.setRange(0.1, 1.0)
        self.kd_value.setDecimals(3)
        self.kd_value.setValue(0.975)
        layout3.addWidget(self.kd_value)
        form_layout.addLayout(layout3)
        
        layout.addWidget(group)
    
    def create_thermo_group(self, layout):
        group = QGroupBox("Termodinamik Model")
        form_layout = QVBoxLayout(group)
        
        layout1 = QHBoxLayout()
        layout1.addWidget(QLabel("Isı Transfer Modeli:"))
        self.heat_model = QComboBox()
        self.heat_model.addItems(["Adiyabatik", "Politropik", "İzotermal"])
        self.heat_model.currentTextChanged.connect(self.on_heat_model_changed)
        layout1.addWidget(self.heat_model)
        form_layout.addLayout(layout1)
        
        self.polytropic_group = QWidget()
        poly_layout = QHBoxLayout(self.polytropic_group)
        poly_layout.addWidget(QLabel("Politropik Üs (n):"))
        self.n_value = QDoubleSpinBox()
        self.n_value.setRange(1.01, 2.0)
        self.n_value.setDecimals(2)
        self.n_value.setValue(1.3)
        poly_layout.addWidget(self.n_value)
        form_layout.addWidget(self.polytropic_group)
        self.polytropic_group.setVisible(False)
        
        layout.addWidget(group)
    
    def create_header_group(self, layout):
        group = QGroupBox("Header/Manifold")
        form_layout = QVBoxLayout(group)
        
        self.header_checkbox = QCheckBox("Header/Manifold Var")
        self.header_checkbox.stateChanged.connect(self.on_header_changed)
        form_layout.addWidget(self.header_checkbox)
        
        self.header_group = QWidget()
        header_layout = QVBoxLayout(self.header_group)
        
        layout1 = QHBoxLayout()
        layout1.addWidget(QLabel("Header Hacmi (m³):"))
        self.v_header = QDoubleSpinBox()
        self.v_header.setRange(0.01, 100)
        self.v_header.setDecimals(3)
        layout1.addWidget(self.v_header)
        header_layout.addLayout(layout1)
        
        layout2 = QHBoxLayout()
        layout2.addWidget(QLabel("Header Başlangıç Basıncı (bar):"))
        self.p_header0 = QDoubleSpinBox()
        self.p_header0.setRange(0.1, 100)
        self.p_header0.setDecimals(1)
        self.p_header0.setValue(1.0)
        layout2.addWidget(self.p_header0)
        header_layout.addLayout(layout2)
        
        layout3 = QHBoxLayout()
        layout3.addWidget(QLabel("Header Sıcaklığı (°C):"))
        self.t_header0 = QDoubleSpinBox()
        self.t_header0.setRange(-50, 200)
        self.t_header0.setDecimals(1)
        self.t_header0.setValue(15.0)
        layout3.addWidget(self.t_header0)
        header_layout.addLayout(layout3)
        
        layout4 = QHBoxLayout()
        layout4.addWidget(QLabel("Boru Uzunluğu (m):"))
        self.l_out = QDoubleSpinBox()
        self.l_out.setRange(0.1, 1000)
        self.l_out.setDecimals(1)
        layout4.addWidget(self.l_out)
        header_layout.addLayout(layout4)
        
        layout5 = QHBoxLayout()
        layout5.addWidget(QLabel("Boru Çapı (mm):"))
        self.d_out = QDoubleSpinBox()
        self.d_out.setRange(1, 1000)
        self.d_out.setDecimals(1)
        layout5.addWidget(self.d_out)
        header_layout.addLayout(layout5)
        
        form_layout.addWidget(self.header_group)
        self.header_group.setVisible(False)
        
        layout.addWidget(group)
    
    def on_gas_type_changed(self, text):
        self.custom_gas_group.setVisible(text == "Özel Karışım")
    
    def on_heat_model_changed(self, text):
        self.polytropic_group.setVisible(text == "Politropik")
    
    def on_header_changed(self, state):
        self.header_group.setVisible(state == Qt.Checked)
    
    def load_defaults(self):
        self.v_system.setValue(8.0)
        self.p0_system.setValue(80.0)
        self.t0_system.setValue(25.0)
        self.target_time.setValue(60)
        self.valve_count.setValue(2)
        self.ch4_percent.setValue(95.0)
        self.c2h6_percent.setValue(3.0)
        self.n2_percent.setValue(2.0)
        self.co2_percent.setValue(0.0)
        self.l_out.setValue(10.0)
        self.d_out.setValue(50.0)
    
    def get_input_params(self):
        params = {
            'V_system': self.v_system.value(),
            'p0_system': self.p0_system.value() * 1e5,
            'T0_system': self.t0_system.value() + 273.15,
            'target_time': self.target_time.value(),
            'valve_count': self.valve_count.value(),
            'valve_params': {
                'Kd': self.kd_value.value(),
                'Kc': 1.0
            },
            'geometry_type': self.geometry_type.currentText().lower(),
            'header_present': self.header_checkbox.isChecked()
        }
        
        gas_type = self.gas_type.currentText()
        if gas_type == "Doğal Gaz":
            params['comp_system'] = {'CH4': 0.95, 'C2H6': 0.03, 'N2': 0.02}
        elif gas_type == "Hava":
            params['comp_system'] = {'N2': 0.79, 'O2': 0.21}
        elif gas_type == "Nitrojen":
            params['comp_system'] = {'N2': 1.0}
        elif gas_type == "CO2":
            params['comp_system'] = {'CO2': 1.0}
        else:
            total = (self.ch4_percent.value() + self.c2h6_percent.value() + 
                    self.n2_percent.value() + self.co2_percent.value()) / 100
            params['comp_system'] = {
                'CH4': self.ch4_percent.value() / 100 / total,
                'C2H6': self.c2h6_percent.value() / 100 / total,
                'N2': self.n2_percent.value() / 100 / total,
                'CO2': self.co2_percent.value() / 100 / total
            }
        
        heat_model = self.heat_model.currentText()
        if heat_model == "Adiyabatik":
            params['heat_model'] = 'adiabatic'
        elif heat_model == "Politropik":
            params['heat_model'] = 'polytropic'
            params['n_value'] = self.n_value.value()
        else:
            params['heat_model'] = 'isothermal'
        
        if params['header_present']:
            params.update({
                'V_header': self.v_header.value(),
                'p_header0': self.p_header0.value() * 1e5,
                'T_header0': self.t_header0.value() + 273.15,
                'L_out': self.l_out.value(),
                'D_out': self.d_out.value() / 1000,
                'eps': 4.5e-5,
                'K_local': 1.0,
                'header_heat': 'isothermal'
            })
        
        return params
    
    def run_simulation(self):
        try:
            input_params = self.get_input_params()
            self.log_text.append("Giriş parametreleri doğrulanıyor...")
            
            self.thread = SimulationThread(input_params)
            self.thread.finished.connect(self.on_simulation_finished)
            self.thread.log.connect(self.log_text.append)
            self.run_button.setEnabled(False)
            self.progress_bar.setRange(0, 0)
            self.thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Giriş parametreleri hatası: {str(e)}")
            self.log_text.append(f"Hata: {str(e)}")
    
    def on_simulation_finished(self, result):
        self.run_button.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        
        if result['success']:
            self.results = result
            self.display_results()
            self.plot_results()
            self.save_button.setEnabled(True)
            self.log_text.append("Simülasyon başarıyla tamamlandı!")
        else:
            QMessageBox.critical(self, "Hata", f"Simülasyon hatası: {result['error']}")
            self.log_text.append(f"Simülasyon hatası: {result['error']}")
    
    def display_results(self):
        result = self.results
        text = f"""BLOWDOWN SİMÜLASYON SONUÇLARI
====================================

GEREKLİ ALAN: {result['A_required']:.2e} m²
SEÇİLEN ORİFİS: {result['selected_label']}
TEK VALF ALANI: {result['A_single']:.2e} m²
TOPLAM ALAN: {result['A_total_selected']:.2e} m²
MARJ: {result['margin']:.1f}%

SONUÇ: {result['report']['verdict']}
NEDEN: {result['report']['verdict_reason']}

UYARILAR:
"""
        for warning in result['report']['warnings']:
            text += f"- {warning}\n"
        
        text += "\nNOTLAR:\n"
        for note in result['report']['notes']:
            text += f"- {note}\n"
        
        self.results_text.setPlainText(text)
    
    def plot_results(self):
        for i in reversed(range(self.plots_layout.count())): 
            self.plots_layout.itemAt(i).widget().setParent(None)
        
        if not self.results:
            return
        
        results = self.results['results']
        
        fig1 = Figure(figsize=(10, 4))
        canvas1 = FigureCanvas(fig1)
        ax1 = fig1.add_subplot(111)
        ax1.plot(results['time'], np.array(results['p_sys']) / 1e5, 'b-', label='Sistem Basıncı (bar)')
        if self.get_input_params()['header_present']:
            ax1.plot(results['time'], np.array(results['p_back']) / 1e5, 'r-', label='Backpressure (bar)')
        ax1.axhline(y=P_ATM/1e5, color='g', linestyle='--', label='Atmosferik Basınç')
        ax1.set_xlabel('Zaman (s)')
        ax1.set_ylabel('Basınç (bar)')
        ax1.legend()
        ax1.grid(True)
        self.plots_layout.addWidget(canvas1)
        
        fig2 = Figure(figsize=(10, 4))
        canvas2 = FigureCanvas(fig2)
        ax2 = fig2.add_subplot(111)
        ax2.plot(results['time'], results['mdot_in'], 'b-', label='Giriş Debi (kg/s)')
        if self.get_input_params()['header_present']:
            ax2.plot(results['time'], results['mdot_out'], 'r-', label='Çıkış Debi (kg/s)')
        ax2.set_xlabel('Zaman (s)')
        ax2.set_ylabel('Kütlesel Debi (kg/s)')
        ax2.legend()
        ax2.grid(True)
        self.plots_layout.addWidget(canvas2)
        
        fig3 = Figure(figsize=(10, 4))
        canvas3 = FigureCanvas(fig3)
        ax3 = fig3.add_subplot(111)
        ax3.plot(results['time'], results['vflow_standard'], 'g-', label='Standart Debi (m³/s)')
        ax3.set_xlabel('Zaman (s)')
        ax3.set_ylabel('Volumetrik Debi (m³/s)')
        ax3.legend()
        ax3.grid(True)
        self.plots_layout.addWidget(canvas3)
    
    def save_results(self):
        if not self.results:
            return
        
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Sonuçları Kaydet", "", "JSON Files (*.json);;Text Files (*.txt)", options=options)
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.results, f, indent=4, default=str)
                self.log_text.append(f"Sonuçlar {filename} dosyasına kaydedildi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Kaydetme hatası: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = BlowdownGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()