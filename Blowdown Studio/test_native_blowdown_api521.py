import sys
import os
import math

# Ekleme Yapılan Dizini Bul
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import importlib.util

spec = importlib.util.spec_from_file_location("blowdown_studio", os.path.join(current_dir, "blowdown_studio.py"))
blowdown_studio = importlib.util.module_from_spec(spec)
sys.modules["blowdown_studio"] = blowdown_studio
spec.loader.exec_module(blowdown_studio)

run_native_blowdown_simulation = blowdown_studio.run_native_blowdown_simulation
find_native_blowdown_area = blowdown_studio.find_native_blowdown_area

def test_typical_pipeline_blowdown():
    print("--- Native Blowdown API 521 Testi ---")
    
    # 1. Geometri ve Proses Şartları
    D_in_m = 0.5   # 500 mm İç çap
    L_m = 1000.0   # 1 km Boru Hattı
    t_m = 0.0127   # 12.7 mm kalınlık (~0.5 in)
    
    V_sys = math.pi * ((D_in_m/2)**2) * L_m
    A_inner = math.pi * D_in_m * L_m
    v_outer = math.pi * (((D_in_m + 2*t_m)/2)**2) * L_m
    M_steel = (v_outer - V_sys) * 7850.0  # Çelik ağırlığı
    
    inputs = {
        'composition': {'Methane': 0.95, 'Ethane': 0.05},
        'V_sys': V_sys,
        'A_inner': A_inner,
        'M_steel': M_steel,
        'p0_pa': 100 * 1e5 + 101325,          # 100 barg -> Pa mutlak
        'T0_k': 50 + 273.15,                  # 50 C -> K
        'p_target_blowdown_pa': 6.89 * 1e5 + 101325, # 6.89 barg (100 psig API 521 hedefi)
        't_target_sec': 900.0                 # 15 dakika (API 521 önerisi)
    }
    
    print(f"Hacim: {V_sys:.2f} m3")
    print(f"Boru Çelik Ağırlığı: {M_steel:.1f} kg")
    
    # Alan Iteratif Bulma
    A_req = find_native_blowdown_area(inputs, progress_callback=None, abort_flag=None)
    print(f"\n=> Gerekli Orifis Alanı: {A_req * 1e6:.2f} mm2")
    assert A_req > 0.0
    
    # Zaman serisi simülasyonu
    print("Simülasyon Çözülüyor (1. Termodinamik Yasa)...")
    df = run_native_blowdown_simulation(inputs, A_req, progress_callback=None, abort_flag=None, silent=False)
    assert not df.empty
    
    print("\n--- Sonuç Özeti ---")
    print(f"Toplam Süre: {df['t'].iloc[-1]:.1f} saniye")
    print(f"Son Basınç: {(df['p_sys'].iloc[-1]-101325)/1e5:.2f} barg")
    print(f"Minimum Gaz Sıcaklığı: {df['T_sys'].min() - 273.15:.2f} C")
    print(f"Minimum Duvar (MDMT) Sıcaklığı: {df['T_wall'].iloc[-1] - 273.15:.2f} C")
    assert df['t'].iloc[-1] <= inputs['t_target_sec'] * 1.05
    assert df['p_sys'].iloc[-1] <= inputs['p_target_blowdown_pa'] * 1.05

    slower_time = run_native_blowdown_simulation(inputs, A_req * 0.5, progress_callback=None, abort_flag=None, silent=True)
    faster_time = run_native_blowdown_simulation(inputs, A_req * 1.5, progress_callback=None, abort_flag=None, silent=True)
    print(f"Küçük alan süresi: {slower_time:.1f} s")
    print(f"Büyük alan süresi: {faster_time:.1f} s")
    assert slower_time > faster_time

if __name__ == '__main__':
    test_typical_pipeline_blowdown()
