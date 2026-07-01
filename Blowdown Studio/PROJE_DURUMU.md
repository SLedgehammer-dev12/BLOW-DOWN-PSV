# Blowdown Studio - Proje Durumu

Son guncelleme: 9 Nisan 2026

## Aktif urun

- Urun adi: `Blowdown Studio`
- Ana giris: `blowdown_studio.py`
- Geriye donuk baslatici: `Blow Down PSV V3.py`
- Eski snapshot ve ikili dosyalar: `legacy/`

## Su anki kapsam

### Aktif hesap motorlari

- Native blowdown motoru
  - Gercek gaz EOS
  - Enerji dengesi
  - Duvar-gaz isi transferi
  - Faz siniri screening uyarilari
- HydDown motoru
  - Ikinci transient motor
  - Paketleme ve import yolu duzeltildi
- Two-Phase Screening motoru
  - Screening-level HEM benzeri yaklasim
  - Kalibre edilmis final two-phase tasarim araci degil
- Segmented Pipeline motoru
  - Line-pack davranisini segmentleyerek cozer
  - Intersegment akis Darcy-Weisbach screening + choked-flow cap ile temsil edilir

### PSV / PRD tarafi

- API 520-1 gas/vapor preliminary sizing
- API 520-1 steam preliminary sizing
- API 520-1 liquid preliminary sizing
- API 521 fire-case screening
- ASME Section XIII screening
- Vendor screening katalog modeli
- Vendor final selection readiness screening
- Vendor import
  - JSON
  - CSV
  - trim / set-pressure / code-stamp / material alanlari destekleniyor
  - inlet / outlet rating class alanlari destekleniyor
  - PSV arayuzunden optional exact vendor filtreleri girilebiliyor
    - trim code
    - code stamp
    - body / trim material
    - inlet / outlet rating class
- PSV raporlama
  - metin raporu
  - CSV export
  - PDF export

### Tank venting tarafi

- API 2000 normal venting screening
- API 2000 emergency venting screening

## Son tamamlanan iyilestirmeler

- `constants.py` ile ortak sabitler tek yerde toplandi
- `materials.py` ile sicakliga bagli karbon celigi `Cp(T)` modeli eklendi
- `thermodynamic_utils.py` ile tekrar eden yardimci fonksiyonlar ortak modula tasindi
  - `build_state`
  - `update_state_from_rho_u_gas`
  - `get_h_inner`
  - `evaluate_phase_screening`
- Native blowdown solver yeni `native_blowdown_engine.py` moduline tasindi
  - `calculate_flow_rate`
  - `parse_outlet_diameter_mm`
  - `calculate_reaction_force`
  - `run_native_blowdown_simulation`
  - `find_native_blowdown_area`
- Blowdown engine dispatch ve rapor akisi yeni `blowdown_workflow.py` moduline tasindi
  - engine secimi
  - standart vana secimi
  - blowdown screening raporu
- PSV sizing workflow'u yeni `psv_workflow.py` moduline tasindi
  - service-type bazli sizing dispatch
  - vendor screening secimi
  - Section XIII screening baglantisi
  - PSV report bundle olusturma
- `ui_file_actions.py` ile dosya odakli UI yardimcilari ayrildi
  - PSV CSV/PDF export dialog akisi
  - save/load settings payload olusturma
  - legacy ayar dosyasi uyumlulugu
- `psv_export_ui_actions.py` ile aktif PSV raporu kontrolu ve export feedback akisi ayrildi
- `api2000_workflow.py` ile API 2000 summary/workflow mantigi UI sinifindan ayrildi
- `api2000_ui_actions.py` ile API 2000 UI payload toplama ve feedback akisi ayrildi
- `vendor_catalog_actions.py` ile aktif katalog cozme ve summary metinleri ayrildi
- `methodology_content.py` ile yardim/metodoloji icerigi UI sinifindan ayrildi
- `ui_mode_logic.py` ile mode degisimi ve PSV service-field karar mantigi UI sinifindan ayrildi
  - field visibility
  - label/unit karar mantigi
  - run button metni ve placeholder secimi
- `ui_builders.py` ile widget construction/layout parcali modullere alinmaya baslandi
  - main settings pane
  - API 2000 pane
  - menu bar
  - gas composition pane
  - right pane / graph host
  - log tab
  - notebook/main shell
  - left pane shell
  - mode help metni ve daha okunur giris gruplari
  - optional exact vendor filtreleri icin ayri panel
  - gaz seciminde Enter / cift tik ile hizli ekleme
  - sonuc ve API 2000 raporlari icin kaydirmali metin alani
- `update_actions.py` ile guncelleme kontrolu ve release asset secim mantigi ayrildi
  - latest release fetch
  - surum karsilastirma
  - exe asset secimi
  - varsayilan indirme yolu
- `update_ui_actions.py` ile update prompt ve async indirme UI reaksiyonlari ayrildi
- `update_flow_actions.py` ile background update kontrolu ve prompt->download zinciri ayrildi
- `ui_display_actions.py` ile text/progress/figure/metodoloji dialog gosterimi ayrildi
- `ui_state_actions.py` ile mode-change ve PSV service-field uygulama mantigi ayrildi
- `composition_actions.py` ile gaz listesi/composition callback mantigi ayrildi
- `input_collection_actions.py` ile blowdown input toplama, fire-case hedef turetimi ve solver-specific validasyonlar ayrildi
- `run_control_actions.py` ile run-button dispatch ve blowdown thread-start orchestration ayrildi
- `vendor_catalog_ui_actions.py` ile vendor import/reset/summary dialog callback'leri ayrildi
- Vendor katalog ozeti exact metadata coverage sayilarini gosterir
  - trim code
  - set-pressure range
  - code stamp
  - body / trim material
- Vendor screening exact metadata varsa su alanlarda filtreleyebilir
  - code stamp
  - body material
  - trim material
  - inlet / outlet rating class
- Spirax SV418 / SV5708 ve Goetze 461 kayitlarinda katalogtan cekilen code-stamp ve kisitli material/rating metadata'si islenmistir
- Farris 2600, Consolidated 1900/3900 ve LESER 526 ailelerinde katalogtan cekilebilen code-stamp ve/veya material/rating metadata'si islenmistir
- Consolidated 1900, Spirax SV418/SV5708 ve Goetze 461 icin katalogtan okunabilen set-pressure araliklari da screening verisine islenmistir
- `psv_ui_actions.py` ile PSV UI input toplama ve workflow sonucu uygulama mantigi ayrildi
- `blowdown_ui_actions.py` ile blowdown execution/orchestration ve report-uygulama oncesi akisi ayrildi
- `execution_ui_actions.py` ile PSV ve blowdown calistirma/feedback akislari ayrildi
- `plotting_actions.py` ile graph placeholder ve PSV/blowdown plotting orchestration'i ana UI dosyasindan ayrildi
- `acoustic_screening.py` yeniden duzenlendi
  - ideal olmayan placeholder akustik guc formulu kaldirildi
  - boyutsal olarak tutarli screening jet-power yaklasimi kullanildi
  - sahte genlik ciktilari kaldirildi
- `api521_discharge_piping.py`
  - sabit pürüzlülük mantigi korunuyor
  - Reynolds sayisi proses kosullarindan hesaplanabiliyor
- liquid PSV tarafinda `Kw` anlami backend seviyesinde duzeltildi
- segmented pipeline solver icin friction modeli siniri acik warning olarak rapora eklendi
- regression benchmark paketi genisletildi

## Test durumu

Aktif test basliklari:

- `test_api520_preliminary.py`
- `test_api520_fluid_services.py`
- `test_api521_fire_case.py`
- `test_asme_section_xiii.py`
- `test_psv_vendor_catalog.py`
- `test_vendor_catalog_import.py`
- `test_psv_reporting.py`
- `test_psv_workflow.py`
- `test_ui_file_actions.py`
- `test_psv_export_ui_actions.py`
- `test_api2000_workflow.py`
- `test_api2000_ui_actions.py`
- `test_vendor_catalog_actions.py`
- `test_methodology_content.py`
- `test_ui_mode_logic.py`
- `test_ui_builders.py`
- `test_update_actions.py`
- `test_update_ui_actions.py`
- `test_update_flow_actions.py`
- `test_ui_display_actions.py`
- `test_ui_state_actions.py`
- `test_composition_actions.py`
- `test_input_collection_actions.py`
- `test_run_control_actions.py`
- `test_vendor_catalog_ui_actions.py`
- `test_psv_ui_actions.py`
- `test_blowdown_ui_actions.py`
- `test_execution_ui_actions.py`
- `test_plotting_actions.py`
- `test_native_blowdown_api521.py`
- `test_hyddown_adapter.py`
- `test_two_phase_flow.py`
- `test_segmented_pipeline.py`
- `test_api2000_emergency.py`
- `test_materials.py`
- `test_regression_benchmarks.py`
- `test_acoustic_screening.py`
- `test_discharge_piping.py`

Silinen test:

- `test_v3_api521.py`
  - artik sadece eski native testin ince wrapper'i idi
  - tekrarli ve dusuk sinyal oldugu icin kaldirildi

## Kalan teknik bosluklar

- `blowdown_studio.py` hala buyuk; ancak native blowdown ve PSV workflow mantigi parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow ve metodoloji icerigi parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi ve mode-state mantigi parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi, mode-state mantigi ve ana widget builder'lari parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi, mode-state mantigi ve menu/pane builder'lari parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi, mode-state mantigi, shell/menu/pane builder'lari ve update yardimcilari parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi, mode-state mantigi, shell/menu/pane builder'lari, update yardimcilari ve plotting orchestration parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi, mode-state mantigi, shell/menu/pane builder'lari, update yardimcilari, update UI reaksiyonlari, display yardimcilari ve plotting orchestration parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi, mode-state mantigi, shell/menu/pane builder'lari, update yardimcilari, update UI reaksiyonlari, display yardimcilari, field-state uygulama mantigi, composition callback'leri ve plotting orchestration parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi, mode-state mantigi, shell/menu/pane builder'lari, update yardimcilari, update UI reaksiyonlari, display yardimcilari, field-state uygulama mantigi, composition callback'leri, input toplama mantigi ve plotting orchestration parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi, mode-state mantigi, shell/menu/pane builder'lari, update yardimcilari, update UI reaksiyonlari, display yardimcilari, field-state uygulama mantigi, composition callback'leri, input toplama mantigi, run/thread-start orchestration, vendor dialog callback'leri ve plotting orchestration parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi, mode-state mantigi, shell/menu/pane builder'lari, update yardimcilari, update UI reaksiyonlari, display yardimcilari, field-state uygulama mantigi, composition callback'leri, input toplama mantigi, run/thread-start orchestration, vendor dialog callback'leri, PSV UI callback mantigi ve plotting orchestration parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, API 2000 workflow, metodoloji icerigi, mode-state mantigi, shell/menu/pane builder'lari, update yardimcilari, update UI reaksiyonlari, display yardimcilari, field-state uygulama mantigi, composition callback'leri, input toplama mantigi, run/thread-start orchestration, vendor dialog callback'leri, PSV UI callback mantigi, blowdown execution akisi ve plotting orchestration parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, PSV export feedback, API 2000 workflow, API 2000 UI feedback, metodoloji icerigi, mode-state mantigi, shell/menu/pane builder'lari, update yardimcilari, update UI reaksiyonlari, display yardimcilari, field-state uygulama mantigi, composition callback'leri, input toplama mantigi, run/thread-start orchestration, vendor dialog callback'leri, PSV UI callback mantigi, blowdown execution akisi ve plotting orchestration parcali modullere alinmaya baslandi
- `blowdown_studio.py` hala buyuk; ancak native blowdown, PSV workflow, file actions, PSV export feedback, API 2000 workflow, API 2000 UI feedback, metodoloji icerigi, mode-state mantigi, shell/menu/pane builder'lari, update yardimcilari, update UI reaksiyonlari, display yardimcilari, field-state uygulama mantigi, composition callback'leri, input toplama mantigi, run/thread-start orchestration, vendor dialog callback'leri, PSV UI callback mantigi, genel PSV/blowdown execution feedback akisi ve plotting orchestration parcali modullere alinmaya baslandi
- Acoustic / AIV tarafi screening-level; Mach, tahmini PWL ve AIV index raporlaniyor ancak final API 521 / EI yorumu degil
- Reaction force tarafi screening-level; exit-plane hiz ve basinç itkisinde tek-kesit yaklasimi kullaniyor ancak tam API 520-2 outlet-plane kuvvet hesabi degil
- Segmented pipeline motorunda Darcy-Weisbach screening var; ancak tam Fanno / distributed momentum cozum yok
- Native ve segmented blowdown motorlari tam iki-faz validated solver degil
- Vendor screening ile final vendor selection arasindaki bosluk daraltildi; readiness checklist ve eksik teyitler raporlaniyor, ancak exact trim/nameplate/vendor approval adimi hala harici teyit ister
- Vendor katalog semasi exact metadata alanlarini destekler; ancak resmi vendor veri setlerinin buyuk bolumunde bu alanlar henuz dolu degildir
- API 2000 normal venting C-factor tablosu sadeleştirilmis screening yaklasimi kullanir

## Bir sonraki mantikli adimlar

1. Acoustic / discharge screening ciktilarini UI tarafinda daha yapisal gostermek
2. Segmented pipeline friction modelini tam compressible pipe momentum / Fanno seviyesine yaklastirmak
3. Vendor datasheet import akisini gercek trim/set-pressure/nameplate verisiyle doldurmak
4. UI workflow katmanini daha da parcali hale getirmek
   - notebook/event orchestration
   - kalan notebook sekme/gecis senkronizasyonlari
   - kalan az sayida UI callback senkronizasyonu
5. Yeni degisiklikleri surumleyip release almak
