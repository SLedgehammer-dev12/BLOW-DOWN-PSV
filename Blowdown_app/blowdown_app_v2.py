import sys
import os
import json
import math
import logging
from logging.handlers import RotatingFileHandler
from collections import OrderedDict
import warnings
from scipy.optimize import fsolve
import scipy.optimize
import numpy as np
import importlib

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
DT_INITIAL = 0.05  # s
DT_MIN = 1e-6  # s
DT_MAX = 5.0  # s
TOL_PRESSURE = 0.03  # 3%

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
        self.logger = logging.getLogger('blowdown_app_v2')
        self.logger.setLevel(logging.INFO)
        fh = RotatingFileHandler('blowdown_app_v2.log', maxBytes=10485760, backupCount=5)
        fh.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def convert_to_coolprop_names(self, composition):
        coolprop_comp = {}
        for gas, fraction in composition.items():
            coolprop_name = self.coolprop_gas_names.get(gas.upper(), gas)
            coolprop_comp[coolprop_name] = fraction
        return coolprop_comp
    
    def gas_props(self, T, p, composition, get_transport_props=False):
        """Gaz özelliklerini hesaplar. Termodinamik simülasyon (Energy Balance) için Transport verilerini de çeker."""
        cache_key = (round(T, 3), round(p, 0), tuple(sorted(composition.items())), get_transport_props)
        if cache_key in self.gas_props_cache:
            return self.gas_props_cache[cache_key]
        
        coolprop_comp = self.convert_to_coolprop_names(composition)
        
        try:
            import CoolProp.CoolProp as CP
            gas_mixture = '&'.join([f'{k}[{v}]' for k, v in coolprop_comp.items()])
            
            MW = CP.PropsSI('M', 'T', T, 'P', p, gas_mixture)
            Z = CP.PropsSI('Z', 'T', T, 'P', p, gas_mixture)
            cp = CP.PropsSI('C', 'T', T, 'P', p, gas_mixture)
            cv = CP.PropsSI('O', 'T', T, 'P', p, gas_mixture)
            k = cp / cv if cv != 0 else 1.4
            R_s = GAS_CONSTANT / MW
            rho = p / (Z * R_s * T)
            a = math.sqrt(k * Z * R_s * T)
            
            props = {
                'MW': MW, 'Z': Z, 'cp': cp, 'cv': cv, 'k': k, 
                'R_s': R_s, 'rho': rho, 'a': a
            }
            
            if get_transport_props:
                cp_mass = CP.PropsSI('C', 'T', T, 'P', p, gas_mixture) # J/kg/K
                viscosity = CP.PropsSI('V', 'T', T, 'P', p, gas_mixture)
                conductivity = CP.PropsSI('L', 'T', T, 'P', p, gas_mixture)
                prandtl = CP.PropsSI('PRANDTL', 'T', T, 'P', p, gas_mixture)
                beta_coeff = CP.PropsSI('ISOBARIC_EXPANSION_COEFFICIENT', 'T', T, 'P', p, gas_mixture)
                props.update({
                    'cpmass': cp_mass,
                    'mu': viscosity,
                    'conductivity': conductivity,
                    'prandtl': prandtl,
                    'beta_coeff': beta_coeff
                })
            else:
                 props['mu'] = CP.PropsSI('V', 'T', T, 'P', p, gas_mixture)

        except Exception as e:
            self.logger.warning(f"CoolProp calculation failed: {e}, using ideal gas approximation")
            props = self.ideal_gas_props(T, p, composition, get_transport_props)
        
        self.gas_props_cache[cache_key] = props
        return props
    
    def ideal_gas_props(self, T, p, composition, get_transport_props=False):
        MW = sum(composition[comp] * self.get_molecular_weight(comp) for comp in composition)
        Z = 1.0
        R_s = GAS_CONSTANT / MW
        k = self.estimate_k_value(composition)
        cp = k * R_s / (k - 1) if k != 1 else 1000
        cv = R_s / (k - 1) if k != 1 else 1000
        rho = p / (R_s * T)
        a = math.sqrt(k * R_s * T)
        mu = self.sutherland_viscosity(T, composition)
        
        props = {'MW': MW, 'Z': Z, 'cp': cp, 'cv': cv, 'k': k, 'R_s': R_s, 'rho': rho, 'a': a, 'mu': mu}
        if get_transport_props:
            props.update({
                'cpmass': cp / MW * 1000,
                'conductivity': 0.03, # approximation W/m.K
                'prandtl': 0.7,
                'beta_coeff': 1/T
            })
        return props
    
    def get_molecular_weight(self, gas_name):
        molecular_weights = {'CH4': 16.04, 'C2H6': 30.07, 'C3H8': 44.10, 'N2': 28.01,
            'CO2': 44.01, 'O2': 32.00, 'H2': 2.02, 'H2O': 18.02, 'AR': 39.95, 'HE': 4.00}
        return molecular_weights.get(gas_name.upper(), 29.0)
    
    def estimate_k_value(self, composition):
        k_values = {'CH4': 1.32, 'C2H6': 1.20, 'C3H8': 1.13, 'N2': 1.40,
            'CO2': 1.29, 'O2': 1.40, 'H2': 1.41, 'H2O': 1.33, 'AR': 1.67, 'HE': 1.66}
        k_mix = sum(fraction * k_values.get(gas.upper(), 1.4) for gas, fraction in composition.items())
        return k_mix
    
    def sutherland_viscosity(self, T, composition):
        # ... Sutherland viscosity implementation ...
        return 1.8e-5 # Fallback simplified
    
    def critical_pressure_ratio(self, k):
        if abs(k - 1.0) < 1e-6:
            return 0.0
        return (2 / (k + 1)) ** (k / (k - 1))
    
    def mdot_choked(self, p_up, T_up, A, k, R_s, Z, C_d):
        if abs(k - 1.0) < 1e-6:
            return C_d * A * p_up * math.sqrt(1 / (R_s * T_up))
        term = math.sqrt(k / (Z * R_s * T_up))
        exponent = (k + 1) / (2 * (k - 1))
        critical_flow_factor = (2 / (k + 1)) ** exponent
        return C_d * A * p_up * term * critical_flow_factor
    
    def mdot_subcritical(self, p_up, p_down, T_up, A, k, R_s, Z, C_d):
        pr = p_down / p_up
        if abs(k - 1.0) < 1e-6:
            return C_d * A * p_up * math.sqrt(2 * math.log(1/pr) / (R_s * T_up))
        term1 = math.sqrt(2 * k / ((k - 1) * Z * R_s * T_up))
        term2 = math.sqrt(pr ** (2 / k) - pr ** ((k + 1) / k))
        return C_d * A * p_up * term1 * term2
    
    def mdot_general(self, p_up, p_down, T_up, A, k, R_s, Z, C_d):
        if p_down >= p_up:
            return 0.0
        pr_crit = self.critical_pressure_ratio(k)
        if pr_crit == 0 or p_down / p_up <= pr_crit:
            return self.mdot_choked(p_up, T_up, A, k, R_s, Z, C_d)
        else:
            return self.mdot_subcritical(p_up, p_down, T_up, A, k, R_s, Z, C_d)
    
    def api_kb_function(self, pressure_ratio):
        if pressure_ratio <= 0.1: return 1.0
        elif pressure_ratio >= 0.5: return 0.6
        else: return 1.0 - 0.8 * (pressure_ratio - 0.1)
    
    def friction_factor_swamee_jain(self, Re, D, eps):
        if Re < 2300: return 64 / max(Re, 1e-6)
        term1 = eps / (3.7 * D)
        term2 = 5.74 / (max(Re, 2300) ** 0.9)
        return 0.25 / (math.log10(term1 + term2) ** 2)
    
    def compute_mdot_out_from_pipe(self, p_up, p_atm, T, D, L, eps, K_local, comp):
        if p_up <= p_atm: return 0.0
        A = math.pi * D**2 / 4
        props = self.gas_props(T, (p_up + p_atm)/2, comp)
        rho, mu = props['rho'], props['mu']
        mdot_max = self.mdot_choked(p_up, T, A, props['k'], props['R_s'], props['Z'], 1.0)
        
        def pressure_drop_eq(mdot_trial):
            if mdot_trial <= 0: return p_up - p_atm
            u = mdot_trial / (rho * A)
            Re = rho * u * D / max(mu, 1e-10)
            f = self.friction_factor_swamee_jain(Re, D, eps)
            delta_p = (f * L/D + K_local) * rho * u**2 / 2
            return delta_p - (p_up - p_atm)
        try:
            mdot_low, mdot_high = 0, mdot_max
            for _ in range(50):
                mdot_mid = (mdot_low + mdot_high) / 2
                f_mid = pressure_drop_eq(mdot_mid)
                if abs(f_mid) < 1: return mdot_mid
                if f_mid > 0: mdot_high = mdot_mid
                else: mdot_low = mdot_mid
            return (mdot_low + mdot_high) / 2
        except:
            return mdot_max

    def get_h_inner(self, T_fluid, T_wall, p_sys, props, D_in, L_sys):
        """Hesapsal iç konveksiyon katsayısı (Energy Balance Model)"""
        if D_in <= 0.0: return 0.0
        
        g = 9.81
        prandtl = props.get('prandtl', 0.7)
        beta_coeff = props.get('beta_coeff', 1/T_fluid)
        mu = props.get('mu', 1.8e-5)
        k_cond = props.get('conductivity', 0.03)
        rho = props.get('rho', 1.0)
        cpmass = props.get('cpmass', 1000)
        
        # Characteristic length
        L_c = L_sys if L_sys < D_in else D_in
        delta_T = abs(T_wall - T_fluid)
        if delta_T < 0.1: return 5.0 # Min fallback
        
        Grashof = (g * beta_coeff * delta_T * (L_c**3) * (rho**2)) / (mu**2)
        Rayleigh = Grashof * prandtl
        
        if Rayleigh < 1e-5:
            Nusselt = 1.0
        elif Rayleigh < 1e9:
            Nusselt = 0.59 * (Rayleigh**0.25)
        else:
            Nusselt = 0.10 * (Rayleigh**0.33)
            
        h_in = (Nusselt * k_cond) / L_c
        return max(0.5, h_in)
    
    def solve_area_for_target_time(self, params, target_time, tol=0.05):
        A_low = 1e-8
        A_high = (params['V_system'] / target_time) * (1 / (0.5 * params['props_sys']['a']))
        
        res_low = self.simulate_blowdown(params, A_low)
        t_low = res_low['time'][-1]
        t_high = self.simulate_blowdown(params, A_high)['time'][-1]
        
        while t_high < target_time:
            A_high *= 2
            if A_high > 1: break
            t_high = self.simulate_blowdown(params, A_high)['time'][-1]
        
        for _ in range(20):
            A_mid = (A_low + A_high) / 2
            results = self.simulate_blowdown(params, A_mid)
            t_final = results['time'][-1]
            if abs(t_final - target_time) / target_time < tol:
                return A_mid
            if t_final < target_time:
                A_high = A_mid
            else:
                A_low = A_mid
        return (A_low + A_high) / 2
    
    def pick_diameter_or_orifice(self, A_required, N, geometry_type):
        if geometry_type == "Orifice": areas = API_520_ORIFICE_AREAS
        else: areas = {size: math.pi * (diameter/2)**2 for size, diameter in ASME_B36_10_PIPES.items()}
        for label, A_single in sorted(areas.items(), key=lambda x: x[1]):
            if N * A_single >= A_required: return label, A_single
        largest_label = max(areas.items(), key=lambda x: x[1])[0]
        largest_area = areas[largest_label]
        return largest_label, largest_area
    
    def simulate_blowdown(self, params, A_total, dt_initial=DT_INITIAL):
        # Unpack params
        V_system = params['V_system']
        p0_system = params['p0_system']
        T0_system = params['T0_system']
        comp_system = params['comp_system']
        valve_count = params['valve_count']
        valve_params = params.get('valve_params', {})
        heat_model = params.get('heat_model', 'adiabatic')
        n_value = params.get('n_value')
        header_present = params.get('header_present', False)
        
        geom = params.get('geometry')
        if heat_model == 'energy_balance' and geom:
            D_in = geom['D_in']
            L_in = geom['L_in']
            t_wall = geom['t_wall']
            A_inner = math.pi * D_in * L_in
            V_solid = math.pi * ((D_in/2 + t_wall)**2 - (D_in/2)**2) * L_in
            M_steel = V_solid * 7850 # kg
            Cp_steel = 460 # J/kgK
            T_wall = T0_system
        else:
            T_wall = T0_system
        
        t = 0
        p_sys = p0_system
        T_sys = T0_system
        props_sys = self.gas_props(T_sys, p_sys, comp_system, get_transport_props=(heat_model=='energy_balance'))
        m_sys = p_sys * V_system / (props_sys['Z'] * props_sys['R_s'] * T_sys)
        
        coolprop_comp = self.convert_to_coolprop_names(comp_system)
        gas_mixture = '&'.join([f'{k}[{v}]' for k, v in coolprop_comp.items()])
        
        if heat_model == 'energy_balance':
            import CoolProp.CoolProp as CP
            try:
                state = CP.AbstractState("HEOS", gas_mixture)
                state.update(CP.PT_INPUTS, p_sys, T_sys)
                U_mass = state.umass()
            except:
                U_mass = props_sys['cv'] * T_sys
        
        if header_present:
            p_back = params['p_header0']
            comp_header = params.get('comp_header', comp_system.copy())
            props_header = self.gas_props(params['T_header0'], p_back, comp_header)
            m_header = p_back * params['V_header'] / (props_header['Z'] * props_header['R_s'] * params['T_header0'])
            T_header0 = params['T_header0']
        else:
            p_back = P_ATM
        
        A_single = A_total / valve_count
        valves = [{'A': A_single, 'Kd': valve_params.get('Kd', 0.975), 
                   'Kb_func': valve_params.get('Kb_func', self.api_kb_function), 'Kc': valve_params.get('Kc', 1.0)} 
                  for _ in range(valve_count)]
        
        results = {'time': [t], 'p_sys': [p_sys], 'T_sys': [T_sys-273.15], 'T_wall': [T_wall-273.15],
                   'p_back': [p_back], 'mdot_in': [0], 'mdot_out': [0]}
        
        dt = dt_initial
        max_time = 10 * params.get('target_time', 3600)
        iteration_count = 0
        
        while p_sys > P_ATM * 1.01 and t < max_time and iteration_count < 20000:
            iteration_count += 1
            try:
                props_sys = self.gas_props(T_sys, p_sys, comp_system, get_transport_props=(heat_model=='energy_balance'))
                
                mdot_in = 0
                for valve in valves:
                    C_d = valve['Kd'] * valve['Kb_func'](p_back / p_sys) * valve['Kc']
                    mdot_valve = self.mdot_general(p_sys, p_back, T_sys, valve['A'], props_sys['k'], props_sys['R_s'], props_sys['Z'], C_d)
                    mdot_in += max(mdot_valve, 0)
                
                # Header Logic Start
                if header_present:
                    mdot_out = self.compute_mdot_out_from_pipe(p_back, P_ATM, T_header0, params['D_out'], params['L_out'], params.get('eps', 4.5e-5), params.get('K_local', 1.0), comp_header)
                    m_header_new = m_header + (mdot_in - mdot_out) * dt
                    props_header = self.gas_props(T_header0, p_back, comp_header)
                    min_header = P_ATM * params['V_header'] / (props_header['Z'] * props_header['R_s'] * T_header0)
                    m_header_new = max(m_header_new, min_header)
                    
                    def res_header(p_new):
                        props_new = self.gas_props(T_header0, p_new, comp_header)
                        return m_header_new - p_new * params['V_header'] / (props_new['Z'] * props_new['R_s'] * T_header0)
                    try:
                        p_back = max(fsolve(res_header, p_back)[0], P_ATM)
                    except: pass
                else: mdot_out = mdot_in
                
                # System Update Logic
                m_fluid_new = m_sys - mdot_in * dt
                min_m_sys = P_ATM * V_system / (props_sys['Z'] * props_sys['R_s'] * T_sys)
                if m_fluid_new < min_m_sys:
                     m_fluid_new = min_m_sys
                
                if heat_model == 'energy_balance':
                    H_mass_out = props_sys['cp'] * T_sys # Simplified Enthalpy tracking, fallback if CP unavailable.
                    if 'CP' in sys.modules:
                         try:
                             state.update(CP.PT_INPUTS, p_sys, T_sys)
                             H_mass_out = state.hmass()
                         except: pass

                    h_in = self.get_h_inner(T_sys, T_wall, p_sys, props_sys, D_in, L_in)
                    Q_in_watts = h_in * A_inner * (T_wall - T_sys)
                    
                    dT_wall = (-Q_in_watts * dt) / (M_steel * Cp_steel)
                    T_wall += dT_wall
                    
                    U_mass_new = (m_sys * U_mass - mdot_in * H_mass_out * dt + Q_in_watts * dt) / m_fluid_new
                    U_mass = U_mass_new
                    
                    if 'CP' in sys.modules:
                        try:
                            # Try native density/energy flash
                            state.update(CP.DmassUmass_INPUTS, m_fluid_new/V_system, U_mass_new)
                            p_sys = state.p()
                            T_sys = state.T()
                        except Exception as e:
                            # Explicit PT Flash Fallback for Supercritical Mixtures
                            dU_mass = U_mass_new - U_mass
                            cv = props_sys['cv']
                            T_guess = T_sys + (dU_mass / cv)
                            rho_new = m_fluid_new / V_system
                            p_guess = props_sys['Z'] * rho_new * (props_sys['R_s']*props_sys['MW']) / props_sys['MW'] * T_guess
                            
                            try:
                                state.update(CP.PT_INPUTS, p_guess, T_guess)
                                p_sys = state.p()
                                T_sys = state.T()
                            except:
                                p_sys = p_guess
                                T_sys = T_guess
                    else:
                        T_sys = U_mass_new / props_sys['cv']
                        p_sys = m_fluid_new * props_sys['Z'] * props_sys['R_s'] * T_sys / V_system
                else: # Adiabatic or Polytropic
                    n = params.get('n_value', 1.0) if heat_model == 'polytropic' else props_sys['k']
                    
                    def residual_sys(p_new):
                        T_new = T_sys * (p_new / p_sys) ** ((n - 1) / n) if abs(n - 1.0) > 1e-6 else T_sys
                        props_new = self.gas_props(T_new, p_new, comp_system)
                        return m_fluid_new - p_new * V_system / (props_new['Z'] * props_new['R_s'] * T_new)
                    try:
                        p_sys_new = max(fsolve(residual_sys, p_sys)[0], P_ATM)
                        if abs(n - 1.0) > 1e-6: T_sys = T_sys * (p_sys_new / p_sys) ** ((n - 1) / n)
                        p_sys = p_sys_new
                    except: pass
                
                m_sys = m_fluid_new
                if header_present: m_header = m_header_new
                
                t += dt
                results['time'].append(t)
                results['p_sys'].append(p_sys)
                results['T_sys'].append(T_sys-273.15)
                results['T_wall'].append(T_wall-273.15)
                results['p_back'].append(p_back)
                results['mdot_in'].append(mdot_in)
                results['mdot_out'].append(mdot_out)
                
                if abs(p_sys - results['p_sys'][-2]) / p_sys < TOL_PRESSURE: dt = min(dt * 1.5, DT_MAX)
                else: dt = max(dt / 2, DT_MIN)
                
            except Exception as e:
                dt /= 2
                if dt < DT_MIN: break
        
        return results
    
    def run_complete_analysis(self, input_params):
        try:
            self.validate_inputs(input_params)
            input_params['props_sys'] = self.gas_props(input_params['T0_system'], input_params['p0_system'], input_params['comp_system'])
            
            A_required = self.solve_area_for_target_time(input_params, input_params['target_time'])
            label, A_single = self.pick_diameter_or_orifice(A_required, input_params['valve_count'], input_params['geometry_type'])
            A_total_selected = input_params['valve_count'] * A_single
            margin = (A_total_selected / A_required - 1) * 100
            
            results = self.simulate_blowdown(input_params, A_total_selected)
            report = self.generate_report(input_params, A_required, label, A_single, margin, results)
            
            return {'success': True, 'A_required': A_required, 'selected_label': label, 'A_single': A_single,
                    'A_total_selected': A_total_selected, 'margin': margin, 'results': results, 'report': report}
        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def validate_inputs(self, params):
        if params['p0_system'] <= P_ATM: raise ValueError("System pressure must be greater than atmospheric")
        if params['T0_system'] <= 0: raise ValueError("System temperature must be positive (Kelvin)")
    
    def generate_report(self, input_params, A_required, label, A_single, margin, results):
        report = {'warnings': [], 'notes': []}
        final_time = results['time'][-1]
        target_time = input_params['target_time']
        if final_time <= target_time:
            report['verdict'] = 'PASS'
            report['verdict_reason'] = f'Achieved time ({final_time:.1f}s) <= target time ({target_time}s)'
        else:
            report['verdict'] = 'FAIL'
            report['verdict_reason'] = f'Achieved time ({final_time:.1f}s) > target time ({target_time}s)'
        return report

class SimulationThread(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    def __init__(self, input_params):
        super().__init__()
        self.input_params = input_params
    def run(self):
        try:
            simulator = BlowdownSimulator()
            result = simulator.run_complete_analysis(self.input_params)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({'success': False, 'error': str(e)})

class BlowdownGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.results = None
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Blowdown Simülasyon V2 (Enerji Balanslı Hibrit)')
        self.setGeometry(100, 100, 1400, 900)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        left_panel = QWidget()
        self.left_layout = QVBoxLayout(left_panel)
        right_panel = QWidget()
        self.right_layout = QVBoxLayout(right_panel)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([450, 950])
        main_layout.addWidget(splitter)
        
        self.create_system_group()
        self.create_gas_composition_group()
        self.create_valve_group()
        self.create_thermo_group()
        self.create_header_group()
        
        btn_ly = QHBoxLayout()
        self.run_btn = QPushButton('Simülasyonu Çalıştır')
        self.run_btn.clicked.connect(self.run_simulation)
        btn_ly.addWidget(self.run_btn)
        self.left_layout.addLayout(btn_ly)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.left_layout.addWidget(self.log_text)
        
        self.tabs = QTabWidget()
        self.right_layout.addWidget(self.tabs)
        self.results_tab = QWidget()
        self.results_layout = QVBoxLayout(self.results_tab)
        self.results_text = QTextEdit()
        self.results_layout.addWidget(self.results_text)
        self.tabs.addTab(self.results_tab, "Sonuçlar")
        
        self.plots_tab = QWidget()
        self.plots_layout = QVBoxLayout(self.plots_tab)
        self.tabs.addTab(self.plots_tab, "Grafikler (MDMT & Basınç)")
        
        self.load_defaults()
        
    def create_system_group(self):
        g = QGroupBox("Sistem Parametreleri")
        ly = QVBoxLayout(g)
        
        l1 = QHBoxLayout()
        l1.addWidget(QLabel("Boru/Kap İç Çapı (m):"))
        self.d_in = QDoubleSpinBox(); self.d_in.setRange(0.01, 10)
        self.d_in.setDecimals(3); self.d_in.setValue(0.5)
        l1.addWidget(self.d_in)
        ly.addLayout(l1)
        
        l2 = QHBoxLayout()
        l2.addWidget(QLabel("Boru/Kap Uzunluğu (m):"))
        self.l_in = QDoubleSpinBox(); self.l_in.setRange(0.1, 5000)
        self.l_in.setDecimals(1); self.l_in.setValue(100.0)
        l2.addWidget(self.l_in)
        ly.addLayout(l2)
        
        l3 = QHBoxLayout()
        l3.addWidget(QLabel("Metal Et Kalınlığı (mm):"))
        self.t_wall = QDoubleSpinBox(); self.t_wall.setRange(1.0, 100)
        self.t_wall.setDecimals(1); self.t_wall.setValue(12.7)
        l3.addWidget(self.t_wall)
        ly.addLayout(l3)
        
        l4 = QHBoxLayout()
        l4.addWidget(QLabel("Başlangıç Basıncı (bar):"))
        self.p0_sys = QDoubleSpinBox(); self.p0_sys.setRange(1, 1000)
        self.p0_sys.setValue(80.0)
        l4.addWidget(self.p0_sys)
        ly.addLayout(l4)
        
        l5 = QHBoxLayout()
        l5.addWidget(QLabel("Başlangıç Sıcaklığı (°C):"))
        self.t0_sys = QDoubleSpinBox(); self.t0_sys.setRange(-50, 200)
        self.t0_sys.setValue(25.0)
        l5.addWidget(self.t0_sys)
        ly.addLayout(l5)
        
        l6 = QHBoxLayout()
        l6.addWidget(QLabel("Hedef Süre (s):"))
        self.t_target = QDoubleSpinBox(); self.t_target.setRange(1, 3600*24)
        self.t_target.setValue(900.0)
        l6.addWidget(self.t_target)
        ly.addLayout(l6)
        
        self.left_layout.addWidget(g)
        
    def create_gas_composition_group(self):
        g = QGroupBox("Gaz Bileşimi")
        ly = QVBoxLayout(g)
        self.ch4 = QDoubleSpinBox(); self.ch4.setValue(95.0)
        self.c2h6 = QDoubleSpinBox(); self.c2h6.setValue(3.0)
        self.n2 = QDoubleSpinBox(); self.n2.setValue(2.0)
        ly.addWidget(QLabel("CH4 (%)"))
        ly.addWidget(self.ch4)
        ly.addWidget(QLabel("C2H6 (%)"))
        ly.addWidget(self.c2h6)
        ly.addWidget(QLabel("N2 (%)"))
        ly.addWidget(self.n2)
        self.left_layout.addWidget(g)
        
    def create_valve_group(self):
        g = QGroupBox("Valf")
        l = QHBoxLayout(g)
        self.v_count = QSpinBox(); self.v_count.setValue(1)
        self.v_geom = QComboBox(); self.v_geom.addItems(["Orifice", "Pipe"])
        l.addWidget(QLabel("Adet:"))
        l.addWidget(self.v_count)
        l.addWidget(self.v_geom)
        self.left_layout.addWidget(g)
        
    def create_thermo_group(self):
        g = QGroupBox("Termodinamik Model")
        l = QVBoxLayout(g)
        self.heat_model = QComboBox()
        self.heat_model.addItems(["1. Termodinamik Yasa (Enerji Balansı)", "Adiyabatik", "Politropik", "İzotermal"])
        l.addWidget(self.heat_model)
        self.left_layout.addWidget(g)
        
    def create_header_group(self):
        g = QGroupBox("Header (İptal Edilebilir)")
        l = QHBoxLayout(g)
        self.h_check = QCheckBox("Aktif")
        self.v_head = QDoubleSpinBox(); self.v_head.setValue(1.0)
        l.addWidget(self.h_check)
        l.addWidget(QLabel("Hacim(m3):"))
        l.addWidget(self.v_head)
        self.left_layout.addWidget(g)
        
    def load_defaults(self): pass
        
    def get_input_params(self):
        V_sys = math.pi * (self.d_in.value()/2)**2 * self.l_in.value()
        hm = self.heat_model.currentText()
        if hm == "Adiyabatik": model = "adiabatic"
        elif hm == "Politropik": model = "polytropic"
        elif hm == "İzotermal": model = "isothermal"
        else: model = "energy_balance"
        
        return {
            'V_system': V_sys,
            'p0_system': self.p0_sys.value() * 1e5,
            'T0_system': self.t0_sys.value() + 273.15,
            'target_time': self.t_target.value(),
            'valve_count': self.v_count.value(),
            'geometry_type': self.v_geom.currentText().lower(),
            'heat_model': model,
            'geometry': {
                'D_in': self.d_in.value(),
                'L_in': self.l_in.value(),
                't_wall': self.t_wall.value() / 1000.0
            },
            'comp_system': {
                'CH4': self.ch4.value()/100.0,
                'C2H6': self.c2h6.value()/100.0,
                'N2': self.n2.value()/100.0
            },
            'header_present': self.h_check.isChecked(),
            'V_header': self.v_head.value(),
            'T_header0': 273.15+15,
            'p_header0': P_ATM,
            'D_out': 0.1,
            'L_out': 10.0
        }
        
    def run_simulation(self):
        self.log_text.append("Simülasyon Başlatılıyor...")
        self.thread = SimulationThread(self.get_input_params())
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def on_finished(self, result):
        if not result['success']:
             self.log_text.append(f"Hata: {result['error']}")
             return
        self.log_text.append("Tamamlandı.")
        self.results = result
        
        txt = f"GEREKLI ALAN: {result['A_required']:.2e} m²\nSEÇİLEN {result['selected_label']} ({result['A_total_selected']:.2e} m²)\n"
        self.results_text.setPlainText(txt)
        
        self.plot_results()

    def plot_results(self):
        for i in reversed(range(self.plots_layout.count())): 
            self.plots_layout.itemAt(i).widget().setParent(None)
            
        r = self.results['results']
        
        fig = Figure(figsize=(10, 8))
        canvas = FigureCanvas(fig)
        
        ax1 = fig.add_subplot(211)
        ax1.plot(r['time'], np.array(r['p_sys'])/1e5, label='Kabin Basıncı')
        ax1.legend(); ax1.grid(True)
        ax1.set_ylabel('Basınç (bar)')
        
        ax2 = fig.add_subplot(212)
        ax2.plot(r['time'], r['T_sys'], label='Gaz Sıcaklığı', color='blue')
        ax2.plot(r['time'], r['T_wall'], label='Metal Duvar Sıcaklığı (MDMT)', color='red', linewidth=2)
        ax2.legend(); ax2.grid(True)
        ax2.set_xlabel('Zaman (s)'); ax2.set_ylabel('Sıcaklık (°C)')
        
        self.plots_layout.addWidget(canvas)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = BlowdownGUI()
    w.show()
    sys.exit(app.exec_())
