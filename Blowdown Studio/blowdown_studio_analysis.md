# Blowdown Studio v2.3.1 — Derinlemesine Mühendislik ve Yazılım Analizi

> **Analiz Tarihi:** 8 Nisan 2026  
> **Kapsam:** Tüm Python kaynak dosyaları, test modülleri, vendor veri modeli, dokümantasyon

---

## İçindekiler

1. [Genel Mimari Değerlendirme](#1-genel-mimari-değerlendirme)
2. [Termodinamik ve Akışkanlar Dinamiği Doğruluğu](#2-termodinamik-ve-akışkanlar-dinamiği-doğruluğu)
3. [API 520 / PSV Sizing Modülü](#3-api-520--psv-sizing-modülü)
4. [API 521 / Blowdown Motor Modülü](#4-api-521--blowdown-motor-modülü)
5. [İki-Faz Akış Modülü (two_phase_flow.py)](#5-i̇ki-faz-akış-modülü)
6. [Discharge Piping Modülü (api521_discharge_piping.py)](#6-discharge-piping-modülü)
7. [Acoustic/AIV Screening Modülü](#7-acousticaiv-screening-modülü)
8. [API 2000 Tank Havalandırma](#8-api-2000-tank-havalandırma)
9. [Vendor Katalog ve Veri Modeli](#9-vendor-katalog-ve-veri-modeli)
10. [HydDown Entegrasyon](#10-hyddown-entegrasyon)
11. [UI / Arayüz ve Kullanılabilirlik](#11-ui--arayüz-ve-kullanılabilirlik)
12. [Kod Kalitesi ve Yazılım Mühendisliği](#12-kod-kalitesi-ve-yazılım-mühendisliği)
13. [Test Altyapısı](#13-test-altyapısı)
14. [Kritik Bug ve Sözdizimi Hataları](#14-kritik-bug-ve-sözdizimi-hataları)
15. [Önceliklendirilmiş Eylem Planı](#15-önceliklendirilmiş-eylem-planı)

---

## 1. Genel Mimari Değerlendirme

### Güçlü Yönler
- Modüler yapıya geçiş başlamış: `psv_preliminary.py`, `psv_vendor_catalog.py`, `hyddown_adapter.py` ayrı dosyalar
- CoolProp tabanlı gerçek gaz EOS kullanımı (HEOS backend)
- Dual-engine yaklaşımı (Yerel Çözücü + HydDown) iyi bir esneklik sunuyor
- Vendor veri modeli JSON tabanlı, genişletilebilir
- Ayarları JSON olarak kaydet/yükle özelliği

### Yapısal Sorunlar

| Sorun | Önem | Açıklama |
|---|---|---|
| Monolitik ana dosya | Yüksek | `blowdown_studio.py` 1900 satır; UI + iş mantığı + hesap motorları iç içe |
| Dead code | Orta | Satır 1707-1726 arası `return` sonrası ulaşılmayan grafik kodu var |
| `two_phase_flow.py` çalışmaz | Kritik | Sözdizimi hatası ve tanımsız referanslar içeriyor |
| `acoustic_screening.py` entegre değil | Orta | Modül mevcut ama hiçbir yerden çağrılmıyor |
| `api521_discharge_piping.py` entegre değil | Orta | Fonksiyonlar import edilmiyor, UI'dan erişilemiyor |

> [!IMPORTANT]
> Ana uygulama dosyası (1900 satır) acil refactoring gerektiriyor. **Model-View ayrımı** yapılarak hesap motorları, UI ve raporlama katmanları bağımsız modüllere taşınmalı.

---

## 2. Termodinamik ve Akışkanlar Dinamiği Doğruluğu

### 2.1 Gerçek Gaz Modeli — CoolProp Kullanımı ✅

CoolProp HEOS backend, çok bileşenli karışımlar için Helmholtz serbest enerji denklemleri kullanır. Bu doğru bir tercih.

### 2.2 Isı Kapasitesi Oranı (k) — İdeal vs Gerçek

```python
# psv_preliminary.py — doğru yaklaşım
k_ideal = cp0_molar / cv0_molar   # İdeal gaz limiti
k_real  = cp_mass  / cv_mass      # Gerçek gaz
```

> [!WARNING]
> **API 520-1 Eq. (9)** açıkça **ideal-gaz Cp/Cv** oranını (`k = Cp⁰/Cv⁰`) kullanır. Kodda `psv_preliminary.py` bu ayrımı doğru yapar, ancak `blowdown_studio.py` içindeki eski `find_psv_area_by_flow_rate()` fonksiyonu **gerçek k = cp_mass/cv_mass** kullanıyor — bu API 520'ye aykırıdır.

**Etkilenen dosya:** [blowdown_studio.py](file:///D:/%C4%B0%C5%9F/Python%20USB/%C3%87al%C4%B1%C5%9Fan%20programlar/@G%C3%BCncelleme/Blow%20Down/Blowdown%20Studio/blowdown_studio.py#L350-L351)

```python
# Satır 350-351 — Sorunlu
k = state.cpmass() / state.cvmass()  # Gerçek k, API 520 için yanlış
```

**Önerilen düzeltme:** PSV sizing'de `psv_preliminary.py` modülünü kullan, eski `find_psv_area_by_flow_rate()` fonksiyonunu kaldır veya deprecate et.

### 2.3 Ses Hızı Hesabı — acoustic_screening.py

```python
# acoustic_screening.py satır 35 — Hatalı
c = math.sqrt(k * 8314.462618 / MW * temperature_k)  # İdeal gaz formülü
```

> [!CAUTION]
> Bu formül **ideal gaz ses hızı** hesaplar. CoolProp'un `state.speed_sound()` metodu zaten gerçek gaz ses hızını verir ve **doğru olan budur**. Mevcut fonksiyon yanlış sonuç üretecektir (özellikle yüksek basınçlarda sapma %5-15 olabilir).

### 2.4 Compressibility Factor (Z) Kullanımı ✅

Z faktörü CoolProp'tan `state.compressibility_factor()` ile alınıyor — doğru.

### 2.5 Enerji Balansı — Blowdown Motoru

```python
# Satır 444 — Enerji denklemi
U_mass = ((U_mass * old_m) + (Q_in_watts * dt) - (H_mass * (old_m - m_fluid))) / m_fluid
```

Bu denklem, 1. Termodinamik Yasa'nın açık sistem uygulamasıdır:

$$dU_{sys} = \delta Q - h_{out} \cdot dm_{out}$$

**Doğru** implementasyon, ancak birkaç iyileştirme noktası var:

| Konu | Durum | Not |
|---|---|---|
| İç enerji denklemi | ✅ Doğru | $U_{new} = (U_{old} \cdot m_{old} + Q \cdot dt - h \cdot \Delta m) / m_{new}$ |
| Isı transferi yönü | ⚠️ Dikkat | `Q_in_watts` pozitif olduğunda duvardan gaza ısı akar; `T_wall` düzeltmesinde işaret doğru |
| Kütle korunumu | ✅ | `m_fluid = old_m - dm_kg_s * dt` |
| Adyabatik seçenek | ✅ | HT kapatılabilir |

### 2.6 Sıcaklık Tahmini — Rho-U Flash

[update_state_from_rho_u_gas](file:///D:/%C4%B0%C5%9F/Python%20USB/%C3%87al%C4%B1%C5%9Fan%20programlar/@G%C3%BCncelleme/Blow%20Down/Blowdown%20Studio/blowdown_studio.py#L283-L331) fonksiyonu:

- CoolProp mixture'larda `DmassUmass` flash desteklemediği için kendi bisection çözücünüz var
- 60 iterasyon limiti ve $1 \times 10^{-6}$ relatif tolerans makul
- Ancak **alt sınırın 60 K** gibi çok düşük tutulması, doğalgaz karışımlarında CoolProp'un iki faz bölgesine girip hata vermesine yol açabilir

> [!TIP]
> Doğalgaz bileşenleri (C₁-C₅) için faz sınırı kontrolü ekleyin: `if T_guess < T_dew → specify_phase(iphase_gas)` kullanmaya devam edin, ancak uyarı verin.

### 2.7 Serbest Konveksiyon Korelasyonu (h_inner)

```python
# Satır 241 — Sorunlu varsayım
L_char = 1.0  # Daima 1 metre
```

> [!WARNING]
> **Karakteristik uzunluk (L_char)** serbest konveksiyon korelasyonlarında **çap** veya **L/D oranı** üzerinden belirlenir. Sabit 1 m varsayımı, DN100 boru için h değerini **fazla**, DN600 tank için **düşük** hesaplar. Bu, MDMT tahmini açısından **güvenli olmayan** sonuçlara yol açabilir.

**Düzeltme:** `L_char = D_inner / 2` (boru) veya `L_char = L_vessel` (tank içi yükseklik) kullanılmalı.

### 2.8 Çelik Fiziksel Özellikleri

```python
Cp_steel = 480.0  # J/(kg·K) — sabit
rho_steel = 7850.0  # kg/m³
```

Karbonlu çelik (API 5L X52/X65) için bu değerler makul. Ancak:
- Düşük sıcaklıklarda çeliğin Cp'si azalır (200K civarında ~350 J/(kg·K))
- Sıcaklık bağımlı bir Cp(T) tablosu daha doğru olur

---

## 3. API 520 / PSV Sizing Modülü

### 3.1 `psv_preliminary.py` — Genel Değerlendirme ✅

Bu modül, API 520 Part I Ed. 10'un gaz/vapor PRV boyutlandırmasını uygun biçimde implement ediyor.

| Özellik | Durum | Referans |
|---|---|---|
| Relieving pressure hesabı | ✅ | $P_1 = P_{set} + (P_{set,gauge} \times \text{overpressure\%}/100)$ |
| Kritik basınç oranı | ✅ | $r_c = (2/(k+1))^{k/(k-1)}$ |
| Coefficient C (SI) | ✅ | Eq. (9) uyumlu |
| Subkritik F₂ katsayısı | ✅ | Eq. (22) uyumlu |
| Balanced bellows Kb mantığı | ✅ | Kritik/subkritik ayrımı yapılmış |
| Conventional subkritik | ✅ | Eq. (19) + Eq. (22) kullanılıyor |
| Pilot-operated | ⚠️ | Backpressure etkisi yok (çünkü pilot-operated valve'da gerçekten minimal), ama açıklama eksik |

### 3.2 Eksik Standart Kapsamı

| Eksik | API Referansı | Önem |
|---|---|---|
| Sıvı servisi sizing | API 520-1 Eq. (32-35) | Yüksek |
| İki fazlı sizing (omega metodu) | API 520-1 Annex D / HEM | Yüksek |
| Buhar (steam) servisi | API 520-1 Eq. (24-27) | Orta |
| Fire case sizing | API 521 §5.15 | Yüksek |
| Kp düzeltmesi | API 520-1 (rupture disk Kp vs Kc) | Düşük |
| Multiple valve kurulumu overpressure | API 520-1 Table 1 | Orta |

> [!IMPORTANT]
> API 520 Part I **Table 1** (ASME BPVC Sec. VIII'den alıntı) birden fazla PRV için farklı overpressure limitleri tanımlar:
> - Tek valf: %10
> - Çoklu valf: İlk valf %10, diğerleri %16
> - Fire case: %21
> 
> Mevcut uygulama bu ayrımı kullanıcıya bırakıyor (girdi olarak). En azından **uyarı** vermeli.

### 3.3 Eski `find_psv_area_by_flow_rate()` — Deprecate Edilmeli

[blowdown_studio.py satır 333-371](file:///D:/%C4%B0%C5%9F/Python%20USB/%C3%87al%C4%B1%C5%9Fan%20programlar/@G%C3%BCncelleme/Blow%20Down/Blowdown%20Studio/blowdown_studio.py#L333-L371):

Bu fonksiyon, `psv_preliminary.py`'daki daha doğru implementasyonun eski bir kopyası. Sorunları:

1. **Gerçek k** kullanıyor (ideal k yerine)
2. **PRV design type** ayrımı yapmıyor
3. **Overpressure** mantığı yok — doğrudan `p0_pa` kullanarak relieving pressure varsayıyor
4. Hâlâ test dosyasından (`test_psv_sizing.py`) çağrılıyor

**Eylem:** Bu fonksiyonu deprecate edip test'i `psv_preliminary.calculate_preliminary_gas_psv_area` üzerinden güncelleyin.

### 3.4 Reaksiyon Kuvveti Hesabı

```python
# Satır 273-281
P_throat = p1_pa * ((2 / (k + 1))**(k / (k - 1)))
T_throat = T1_k * (2 / (k + 1))
v_throat = math.sqrt(k * R_spec * T_throat)
F_newtons = W_kg_s * v_throat + (P_throat - P_ATM) * A_orifice_m2
```

> [!WARNING]
> API 520-2 §E.6'daki reaksiyon kuvveti formülü:
> $$F = \dot{m} \cdot v_e + (P_e - P_a) \cdot A_e$$
> 
> Burada $A_e$ **outlet/exit alanıdır**, orifis alanı değil. Mevcut kodda `A_orifice_m2` kullanılıyor — bu outlet pipe alanı yerine orifis alanı olabilir. Eğer orifis alanı kullanılıyorsa, sonic throat koşullarında doğru olabilir (çünkü bogaz = orifis), ancak bir PSV'de discharge piping çıkış alanı farklıdır.
> 
> Ayrıca bu formül sadece **gaz/buhar** servisi içindir — iki fazlı veya sıvı servisinde farklı yaklaşım gerekir.

---

## 4. API 521 / Blowdown Motor Modülü

### 4.1 Yerel Çözücü (Native Engine)

**Doğru olan:**
- 1. Yasa enerji dengesi yaklaşımı
- CoolProp EOS ile gerçek gaz davranışı
- Adaptif zaman adımı (basınç değişimine bağlı)
- Metal duvar — gaz ısı transferi etkileşimi

**Geliştirilmesi gereken:**

| Konu | Öncellik | Detay |
|---|---|---|
| Tek hacim modeli | Yüksek | Uzun pipeline'larda dalga yayılımı ve line-pack etkisi ihmal ediliyor |
| Faz değişimi kontrolü | Yüksek | Sıcaklık düştüğünde çiğlenme noktasının altına inilirse CoolProp çökebilir; faz kontrol mekanizması yok |
| Cd değerinin sabitliği | Orta | API 520 Kd ile blowdown Cd farklı şeyler olabilir; gerçek ball valve Cv'si kullanılabilir |
| Multiphase dropout | Yüksek | Doğalgaz blowdown'da -40°C altında hidrokarbon kondensasyonu başlar; tek faz varsayımı güvensiz |
| Boru sürtünmesi | Yüksek | Uzun pipeline blowdown'da sürtünme basınç kaybı önemlidir; ihmal edilmiş |

### 4.2 Boyutlandırma Algoritması (Bisection)

```python
A_low, A_high = 1e-8, 2.0   # m²
max_iter = 35
```

> [!TIP]
> 2.0 m² üst sınır **çok büyük** — bu fiziksel olarak yaklaşık 1.6 m çaplı bir daireye karşılık gelir. Pratikte en büyük API 526 T orifisi ~0.0168 m²'dir. Daha dar bir aralıkla başlamak (ör. geometriden türetilmiş) yakınsamayı hızlandırır.

### 4.3 Discharge Coefficient (Cd) vs Kd Karışıklığı

Kodda `Cd` ismiyle hem:
- API 520 **Kd** (effective coefficient of discharge — sertifikalı) 
- Gerçek **Cd** (discharge coefficient — orifice/ball valve gerçek akış katsayısı)

kullanılıyor. Bunlar farklı büyüklüklerdir:
- **Kd (API 520):** 0.975 (gaz), 0.65 (sıvı) — ASME sertifikalı kapasite hesabında
- **Cd (gerçek):** Ball valve için 0.60-0.85, orifis için ~0.62

**Eylem:** İsimlendirmeyi netleştirin — blowdown motoru için `Cd_valve`, PSV sizing için `Kd_api520`.

---

## 5. İki-Faz Akış Modülü

> [!CAUTION]
> **`two_phase_flow.py` çalıştırılamaz durumdadır.** Birden fazla kritik hata içerir.

### 5.1 Sözdizimi Hatası — Satır 174

```python
# Satır 174 — HATA
X = (1 - x) / x * (rho_v / rho_l)**0.5 * (h_fg / h_l)**0333
#                                           ^^^^   ^^^^
#                                     tanımsız     nokta eksik → 0.333 olmalı
```

- `h_fg` ve `h_l` tanımlanmamış
- `**0333` geçersiz Python sözdizimi — `**0.333` olmalı

### 5.2 CoolProp Kullanım Hatası — Satır 48-55

```python
state_v = CP.AbstractState("HEOS", "&".join(components))
state_v.set_mole_fractions([gas_mole_fraction])  # YANLIŞ
```

`set_mole_fractions`, **bileşen sayısı kadar** fraksiyon bekler (ör. `[0.95, 0.05]`). Burada tek elemanlı bir liste veriliyor ancak `components` listesinde birden fazla bileşen olabilir.

### 5.3 Konsept Hatası — Quality

Vapor quality (x), bir **termodinamik durum değişkenidir** ve basınç+sıcaklıkla birlikte EOS'tan gelir. Kodda sabit `quality = 0.1` varsayılıyor — bu fiziksel olarak anlamsız.

### 5.4 Tanımsız Fonksiyon Referansları

- `update_state_from_rho_u_gas()` — bu `blowdown_studio.py`'da tanımlı ancak `two_phase_flow.py`'da import edilmemiş
- `get_h_inner()` — aynı şekilde eksik import

### 5.5 Progress Callback Mantık Hatası — Satır 317

```python
if not progress_callback and int(t/max(0.001, dt)) % 20 == 0:
    progress_callback(t, target_time)  # None.call → hata
```

`not progress_callback` True olduğunda `progress_callback` None'dır — çağrı yapılamaz.

**Sonuç:** Bu modül **tamamen yeniden yazılmalıdır.** Mevcut haliyle ne çalıştırılabilir ne de fiziksel olarak doğrudur.

---

## 6. Discharge Piping Modülü

### 6.1 Sürtünme Faktörü Hatası

```python
# Satır 41 — HATA
roughness = 0.045 * pipe_diameter_mm / 1000  # Bu pürüzlülüğü çapla orantılı yapıyor!
```

Karbon çeliğin yüzey pürüzlülüğü (ε) **sabit** bir malzeme özelliğidir:
- Yeni karbon çelik: ε ≈ 0.045 mm
- Kullanılmış çelik: ε ≈ 0.15 mm
- Paslanmaz çelik: ε ≈ 0.015 mm

Mevcut formül `ε = 0.045 × D` yapıyor — bu fiziksel olarak **yanlıştır** ve büyük çaplarda aşırı sürtünme, küçük çaplarda düşük sürtünme verir.

**Düzeltme:**
```python
roughness_mm = 0.045  # mm (sabit — yeni karbon çelik)
epsilon_D = roughness_mm / pipe_diameter_mm
```

### 6.2 Reynolds Sayısı

```python
Re = 100000  # Sabit varsayım
```

Gerçek Re sayısı debi ve gaz özelliklerinden hesaplanmalı. `Re = ρvD/μ`. PSV discharge'da Re genellikle $10^5 - 10^7$ aralığındadır, ancak sabit değer kullanmak f faktöründe %20-50 sapma yapabilir.

### 6.3 Fitting K Değerleri

Mevcut değerler kabaca doğru ancak:
- API 520 Part II/API 521 referansı yerine **Crane TP-410** K değerleri kullanılmalı
- K değerleri genellikle **fully turbulent** koşullar için verilir ve `K = f_T × (L/D)` formundadır

### 6.4 Entegrasyon Eksikliği

Bu modül hiçbir yerden çağrılmıyor — tanımlanmış ama kullanılmıyor.

---

## 7. Acoustic/AIV Screening Modülü

### 7.1 Ses Hızı — Fizik Hatası

```python
# Satır 35
c = math.sqrt(k * 8314.462618 / MW * temperature_k)
```

Bu **ideal gaz** ses hızı formülüdür:
$$c_{ideal} = \sqrt{\frac{k R T}{M}}$$

**Sorunlar:**
- Z faktörü dahil edilmemiş: $c = \sqrt{\frac{k Z R T}{M}}$
- CoolProp `state.speed_sound()` zaten gerçek gaz ses hızını verir — bu kullanılmalı
- Yüksek basınçlarda (>50 bar) sapma >%10 olabilir

### 7.2 Akustik Güç Formülü — Yanlış

```python
acoustic_power_w = 0.5 * acoustic_velocity_m_s * A_pipe * frequency_hz
```

Bu formül **akustik güç** hesabı değildir. API 521'de sound power level (PWL):

$$PWL = 10 \log_{10}\left(\frac{\dot{m} \cdot c^2 \cdot \eta}{W_0}\right)$$

burada η akustik verim faktörüdür (~0.001 - 0.01).

Mevcut formül boyutsal olarak bile tutarsız (W/m²·s) ve fiziksel olarak anlamsız.

### 7.3 AIV Vibrasyon — Aşırı Basitleştirilmiş

```python
amplitude_mm = mach_number * 0.1  # "Simplified"
```

Bu bir mühendislik hesabı değil, tahminin de ötesinde bir placeholder.

**Sonuç:** Acoustic modül ciddi bir yeniden yazım gerektirir. Mach screening mantığı `blowdown_studio.py`'daki PSV sizing raporunda zaten daha doğru implement edilmiş.

---

## 8. API 2000 Tank Havalandırma

### 8.1 Doğruluk

API 2000 7th Edition Tablo-based yaklaşımı basitleştirilmiş ancak temel mantık doğru:

| Parametre | Durum | Not |
|---|---|---|
| C-faktörü enlem tablosu | ⚠️ | 7th Ed'de daha detaylı tablolar var; yalnızca 3 bant kullanılmış |
| Termal outbreathing katsayısı | ⚠️ | `V_OT = 0.6 × V_IT` basitleştirmesi her koşulda geçerli değil |
| Pompa etkisi çarpanları | ✅ | 1.01 ve 1.07/2.0 değerleri standart ile uyumlu |
| İzolasyon faktörü (Ri) | ✅ | Doğrudan çarpan olarak kullanılıyor |

### 8.2 Eksiklikler

- External fire exposure (emergency venting) hesabı yok
- Hexane factor / true vapor pressure etkisi yok
- Tank içi pad gas etkisi yok
- API 2000 Annex B (termal hesap detayları) eksik

---

## 9. Vendor Katalog ve Veri Modeli

### 9.1 Güçlü Yönler ✅
- JSON tabanlı, genişletilebilir veri modeli
- Built-in fallback katalog
- Kb curve interpolasyon mantığı düzgün
- Conservative envelope (en düşük Kb'yi alan) yaklaşımı doğru mühendislik pratiği

### 9.2 Geliştirmeler

- **Certified capacity hesabı:** Subkritik durumda `capacity` hesabında birim karışıklığı olabilir (satır 357-366), çıktının kg/h birimi olduğu doğrulanmalı
- **Vendor Kd vs API Kd:** Her vendor'ın sertifikalı Kd'si farklıdır (ör. Farris: 0.878, Consolidated: 0.873). Mevcut modelde `certified_kd_gas` alanı var — çok iyi. Ancak not disclaimer test edilmemiş vendor'lar için yetersiz.

---

## 10. HydDown Entegrasyon

### 10.1 Genel Değerlendirme ✅
- Path discovery mantığı (PyInstaller `_MEIPASS` dahil) iyi tasarlanmış
- Composition string builder doğru
- Hata yönetimi makul

### 10.2 Potansiyel Sorunlar

| Sorun | Detay |
|---|---|
| Heat transfer "calc" modu | `"h_inner": "calc"` — HydDown'ın bu modu nasıl yorumladığı dokümante edilmemiş |
| Bisection area limiti | `max_area_m2 = D²π/4` yani boru kesit alanı — mantıklı bir üst sınır |
| Zaman adımı seçimi | `time_step = max(0.25, min(5.0, t_target/500))` — uygun aralık |

---

## 11. UI / Arayüz ve Kullanılabilirlik

### 11.1 Genel

Tkinter tabanlı arayüz fonksiyonel ancak:

| Konu | Öneri |
|---|---|
| Grafik düzeni | 4×3 = 12 subplot çoğu zaman boş kalıyor; dinamik subplot sayısı kullanın |
| CSV export | Blowdown sonuçları için var, PSV tarafı eksik |
| PDF rapor | PROJE_DURUMU.md'de planlanmış, henüz yok |
| Birim sistemi tutarlılığı | Kullanıcı SI veya US Customary seçebilmeli |
| Input doğrulama | Negatif sıcaklık, sıfır debi gibi fiziksel olmayan girdiler için yeterli kontrol yok |

### 11.2 Ölü Kod (Dead Code)

[blowdown_studio.py satır 1707-1726](file:///D:/%C4%B0%C5%9F/Python%20USB/%C3%87al%C4%B1%C5%9Fan%20programlar/@G%C3%BCncelleme/Blow%20Down/Blowdown%20Studio/blowdown_studio.py#L1707-L1726): `return` statement'tan sonra bulunan ulaşılmaz kod bloğu silinmeli.

### 11.3 Thread Safety

```python
# Satır 206-210 — TkinterHandler
self.text_widget.config(state=tk.NORMAL)
self.text_widget.insert(tk.END, msg + "\n", record.levelname)
```

`after(0, append)` kullanılıyor — bu doğru. Ancak hesaplama thread'inden UI güncellemesi yapan bazı yerlerde `self.after()` kullanılmamış olabilir — dikkat edilmeli.

---

## 12. Kod Kalitesi ve Yazılım Mühendisliği

### 12.1 Tekrarlanan Sabitler

`R_U = 8314.462618` ve `P_ATM = 101325` en az **4 farklı dosyada** yeniden tanımlanıyor. Tek bir `constants.py` modülü oluşturulmalı.

### 12.2 İsimlendirme Tutarsızlıkları

- `Cd` vs `Kd` — farklı kavramlar ama aynı isimle kullanılıyor
- `p0_pa` — bazı yerlerde set pressure, bazı yerlerde başlangıç basıncı
- Türkçe-İngilizce karışık: `zaman_serisi`, `vana_alani_m2` vs `pressure_ratio`

### 12.3 Hata Yönetimi

```python
except Exception as e:
    return 10.0  # Safe fallback
```

Genel `Exception` yakalama çok geniş. CoolProp hatalarını (`ValueError`, `RuntimeError`) spesifik olarak yakalayın ve kullanıcıya anlamlı mesaj verin.

### 12.4 Tekrarlanan Satır

```python
# Satır 257-258 — Aynı satır iki kez
h_inner = Nu * cond / L_char
h_inner = Nu * cond / L_char  # Duplike
```

---

## 13. Test Altyapısı

### 13.1 Mevcut Durum

| Test | Kapsam | Kalite |
|---|---|---|
| `test_api520_preliminary.py` | Kritik/subkritik/balanced | ✅ İyi — API 520 örneğiyle karşılaştırma |
| `test_native_blowdown_api521.py` | Pipeline blowdown | ✅ Temel kontroller |
| `test_psv_sizing.py` | Eski fonksiyon | ⚠️ Eski (deprecate edilmeli) |
| `test_psv_vendor_catalog.py` | Vendor modeli | ✅ Kapsamlı |
| `test_hyddown_adapter.py` | HydDown builder | ⚠️ Sadece input build |
| `test_v3_api521.py` | — | ❌ Boş (sadece import) |

### 13.2 Eksik Test Senaryoları

- **Fire case** blowdown senaryosu
- **Çok bileşenli** (5+ bileşen) karışım testi
- **Yüksek backpressure** PSV senaryosu
- **Negatif** ve **sınır** değer testleri (edge case)
- API 520 Appendix D'deki **standart benchmark örnekleri**
- **Regression test** ile eski sonuçların korunduğunu doğrulama

---

## 14. Kritik Bug ve Sözdizimi Hataları

> [!CAUTION]
> Aşağıdaki hatalar **acil düzeltilmeli**:

### Bug #1: `two_phase_flow.py` — Sözdizimi hatası (satır 174)
```python
X = ... * (h_fg / h_l)**0333  # SyntaxError + NameError
```

### Bug #2: `two_phase_flow.py` — Progress callback mantık hatası (satır 317)
```python
if not progress_callback and ... :
    progress_callback(t, ...)  # NoneType çağrısı → crash
```

### Bug #3: `two_phase_flow.py` — Return mantık hatası (satır 322-326)
```python
if progress_callback:  # silent modda değil ama progress varsa
    return t           # DataFrame yerine float dönüyor → tutarsız
```

### Bug #4: `api521_discharge_piping.py` — Pürüzlülük formülü (satır 41)
```python
roughness = 0.045 * pipe_diameter_mm / 1000  # Çapa orantılı — yanlış
```

### Bug #5: `acoustic_screening.py` — Ses hızı formülü (satır 35)
Z faktörü eksik, ideal gaz varsayımı yüksek basınçlarda >%10 hata.

### Bug #6: `blowdown_studio.py` — Tekrarlanan satır (satır 257-258)
```python
h_inner = Nu * cond / L_char
h_inner = Nu * cond / L_char  # Gereksiz tekrar
```

### Bug #7: `blowdown_studio.py` — Dead code (satır 1707-1726)
`return` sonrası ulaşılmaz grafik kodu.

---

## 15. Önceliklendirilmiş Eylem Planı

### 🔴 P0 — Acil (Çalışmayı Engelleyen Hatalar)

1. **`two_phase_flow.py` tamamen yeniden yaz** veya devre dışı bırak
   - Sözdizimi hataları, tanımsız referanslar, fizik hataları
   
2. **`api521_discharge_piping.py` sürtünme hesabını düzelt**
   - Pürüzlülük: `roughness_mm = 0.045` (sabit)
   - Reynolds sayısı: Debi ve özelliklerden hesapla

3. **Ölü kodu temizle**
   - `blowdown_studio.py` satır 1707-1726 sil
   - Tekrarlanan satır 258'i sil

---

### 🟠 P1 — Yüksek Öncelik (Mühendislik Doğruluğu)

4. **Eski `find_psv_area_by_flow_rate()` fonksiyonunu kaldır**
   - Gerçek k kullanıyor (ideal k olmalı)
   - `psv_preliminary.py` ile fonksiyonelliği çakışıyor

5. **Serbest konveksiyon L_char düzelt**
   - `L_char = D_inner / 2` (boru geometrisi)
   - Tank/vessel modu için ayrı mantık

6. **Reaksiyon kuvvetinde outlet area kullan**
   - `A_orifice` yerine `A_outlet_pipe` kullan
   - API 520-2 §E.6 ile tam uyum sağla

7. **Acoustic screening modülünde CoolProp `speed_sound()` kullan**
   - İdeal gaz formülünü kaldır

8. **Faz değişimi kontrolü ekle**
   - Blowdown sırasında çiğlenme noktası takibi
   - Kullanıcıya uyarı: "Sıcaklık dew point'in altına indi"

---

### 🟡 P2 — Orta Öncelik (Standart Uyum ve Kullanılabilirlik)

9. **Cd vs Kd isimlendirmesini netleştir**
10. **Sabitleri `constants.py` modülüne taşı**
11. **Acoustic/AIV ve discharge piping modüllerini UI'a entegre et**
12. **API 520 sıvı ve steam sizing ekle**
13. **Fire case sizing (API 521 §5.15) ekle**
14. **CSV/PDF export PSV tarafına da ekle**
15. **Monolitik `blowdown_studio.py` refactor et**
    - `engine.py` (hesap motorları)
    - `ui.py` (Tkinter arayüz)
    - `report.py` (raporlama)
    - `constants.py` (sabitler)

---

### 🟢 P3 — Düşük Öncelik (Gelecek Geliştirmeler)

16. **Segmentli pipeline transient modeli**
17. **Vendor datasheet import akışı**
18. **ASME Section XIII doğrulama adımı**
19. **Regression test benchmark paketi** (API 520 App. D örnekleri)
20. **Sıcaklık bağımlı çelik Cp(T) tablosu**
21. **API 2000 emergency venting (fire case)**

---

> [!NOTE]
> Bu analiz, mevcut kodun **production-grade mühendislik aracı** olarak kullanılabilirliğini değerlendirmektedir. Temel termodinamik yaklaşım (1. Yasa enerji dengesi, CoolProp EOS, API 520 denklemleri) sağlam bir temeldedir. Ancak yardımcı modüller (`two_phase_flow`, `acoustic_screening`, `api521_discharge_piping`) henüz olgunlaşmamış ve kritik hatalar içermektedir. Öncelik, ana motorun doğruluğunu pekiştirmek ve çalışmayan modülleri ya düzeltmek ya da kapsamdan çıkarmak olmalıdır.
