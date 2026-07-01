# Standard Alignment Roadmap

Bu belge, Blowdown Studio'nun API 520, API 521, API 2000 ve ASME Section XIII ile hizalanma durumunu ozetler.

Son guncelleme: 9 Nisan 2026

## Tamamlanan ana maddeler

### API 520 / PSV preliminary sizing

- Gas / vapor preliminary sizing moduler hale getirildi
- Steam preliminary sizing eklendi
- Liquid preliminary sizing eklendi
- Legacy `find_psv_area_by_flow_rate()` artik deprecate bridge olarak kaliyor
- Liquid service tarafinda `Kw` semantigi backend'de kabul ediliyor

### PSV screening ve reporting

- Vendor screening JSON katalogtan ayrildi
- CSV / JSON vendor import eklendi
- Vendor katalog semasi trim / set-pressure / code-stamp / material alanlarini destekler hale getirildi
- Vendor screening exact metadata varsa code-stamp / material / rating-class bazli filtreleme yapabilir
- PSV UI tarafi optional exact vendor filtrelerini toplayip workflow'a aktarir
  - trim code
  - code stamp
  - body / trim material
  - inlet / outlet rating class
- Spirax ve Goetze icin kisitli gercek code-stamp / material metadata'si resmi kataloglardan islenmistir
- Farris, Consolidated ve LESER ailelerinde de katalogtan okunabilen code-stamp / material / rating metadata'si eklenmistir
- Consolidated 1900, Spirax ve Goetze ailelerinde katalogtan okunabilen set-pressure range metadata'si eklenmistir
- ASME Section XIII screening eklendi
- Vendor final selection readiness screening eklendi
- PSV CSV ve PDF export eklendi

### API 521 / blowdown

- Native blowdown motorunda enerji dengesi, isi transferi ve faz siniri screening'i var
- HydDown ikinci motor olarak baglandi
- Two-Phase Screening motoru eklendi
- Segmented Pipeline motoru eklendi
- Fire-case blowdown screening eklendi

### API 2000

- Normal venting screening mevcut
- Emergency venting screening mevcut

### Yazilim kalitesi

- `constants.py` eklendi
- `materials.py` ile `Cp(T)` eklendi
- `thermodynamic_utils.py` ile tekrar eden termodinamik yardimcilari ortaklastirildi
- `native_blowdown_engine.py` ile native solver ana UI dosyasindan ayrildi
- `blowdown_workflow.py` ile blowdown dispatch ve raporlama akisi UI sinifindan ayrilmaya basladi
- `psv_workflow.py` ile PSV sizing, vendor screening ve report bundle akisi UI sinifindan ayrilmaya basladi
- `ui_file_actions.py` ile settings persistence ve PSV export dialog akisi UI sinifindan ayrilmaya basladi
- `psv_export_ui_actions.py` ile aktif PSV raporu kontrolu ve export feedback akisi ayrildi
- `api2000_workflow.py` ile API 2000 hesap ozeti ve emergency workflow akisi UI sinifindan ayrilmaya basladi
- `api2000_ui_actions.py` ile API 2000 UI payload toplama ve feedback akisi ayrildi
- `vendor_catalog_actions.py` ile katalog summary/mesaj olusturma ayrildi
- `methodology_content.py` ile yardim/metodoloji icerigi ayrildi
- `ui_mode_logic.py` ile mode degisimi, field visibility ve service-field label/unit kararlari ayrildi
- `ui_builders.py` ile main settings ve API 2000 widget construction/layout kodu ayrilmaya basladi
- `ui_builders.py` artik menu, log tab, gas composition ve right-pane widget kurulumlarini da tasiyor
- `ui_builders.py` artik notebook/main shell ve left-pane shell kurulumlarini da tasiyor
- UI ergonomisi iyilestirildi
  - mode help metni
  - optional exact vendor filtreleri icin ayri panel
  - gaz kompozisyonunda Enter / cift tik ile hizli ekleme
  - uzun sonuc metinleri icin kaydirmali rapor alani
- `update_actions.py` ile update kontrolu ve release asset secim mantigi ayrildi
- `update_ui_actions.py` ile update prompt ve async indirme UI reaksiyonlari ayrildi
- `update_flow_actions.py` ile background update kontrolu ve prompt->download akisi ayrildi
- `ui_display_actions.py` ile text/progress/figure/metodoloji dialog gosterimi ayrildi
- `ui_state_actions.py` ile mode-change ve PSV service-field uygulama mantigi ayrildi
- `composition_actions.py` ile gaz listesi/composition callback mantigi ayrildi
- `input_collection_actions.py` ile blowdown input toplama ve fire-case hedef turetimi ayrildi
- `run_control_actions.py` ile run-button dispatch ve blowdown thread-start orchestration ayrildi
- `vendor_catalog_ui_actions.py` ile vendor import/reset/summary dialog callback'leri ayrildi
- `psv_ui_actions.py` ile PSV UI input toplama ve workflow sonucu uygulama mantigi ayrildi
- `blowdown_ui_actions.py` ile blowdown execution/orchestration ve report-uygulama oncesi akis ayrildi
- `execution_ui_actions.py` ile PSV ve blowdown calistirma/feedback akislari ayrildi
- `plotting_actions.py` ile graph placeholder ve PSV/blowdown plotting orchestration'i ayrildi
- `test_v3_api521.py` kaldirildi
- Regression benchmark paketi eklendi

## Halen screening seviyesinde kalan maddeler

1. Reaction force
   - `calculate_reaction_force()` exit-plane hiz + basinç itkisinde tek-kesit screening yaklasimi kullanir
   - Tam API 520-2 outlet-plane reaction force hesabi degildir

2. Acoustic / AIV
   - Akustik guc artik boyutsal olarak tutarli screening mantigi kullanir
   - Screening PWL ve AIV index raporlanir
   - Buna ragmen final API 521 / EI acoustic fatigue calismasi yerine gecmez
   - AIV genlik placeholder'i kaldirildi; yalniz screening indeks kaldi

3. Segmented pipeline friction
   - Segmentler arasi akista Darcy-Weisbach screening + choked-flow cap kullanilir
   - Buna ragmen tam compressible Fanno / distributed momentum cozum yok
   - Raporda warning olarak belirtilir

4. API 2000 normal venting
   - C-factor ve thermal outbreathing sadeleştirilmis screening tablosu ile hesaplanir
   - Final vendor / standard table verification gerektirir

## Kalan teknik bosluklar

1. `blowdown_studio.py` refactor
   - Native solver, PSV workflow, dosya odakli UI yardimcilari, API 2000 workflow, metodoloji icerigi, mode-state mantigi, menu/pane builder kodu ve update helper mantigi ayrildi
   - UI/event ve form-state orchestration katmani incelmeye devam etti
   - Kalan ana agirlik daha cok notebook/event, sekme gecisleri ve bazi son UI callback baglantilarinda
   - API 2000 calistirma ve PSV export UI callback bloklari da ayrildi

2. Native / segmented engine ayrisma
   - Native solver ayrildi
   - Segmented / two-phase / HydDown orchestration tarafinda halen ek parcalama alani var

3. Full discharge network
   - API 520-2 / 521 discharge system modellemesi screening disinda kalir

4. Final vendor selection
   - Screening ile final certified vendor selection arasinda hala bosluk var
   - Exact-field schema hazir; ancak gercek vendor veri setlerinin trim/set-pressure/nameplate alanlari henuz sinirli

5. Full two-phase validation
   - Screening-level two-phase ve segmented yaklasimlar validated HEM/DI cozumleri yerine gecmez

## Onerilen sonraki sira

1. `blowdown_studio.py` icindeki kalan UI/workflow/event mantigini ayri modullere tasimak
   - kalan notebook/event senkronizasyonlari
   - kalan az sayida UI callback senkronizasyonu
   - kalan plotting/event senkronizasyonlari
2. Segmented pipeline friction modelini tam compressible pipe momentum / Fanno seviyesine yaklastirmak
3. Acoustic/AIV screening'i UI ve raporda daha sistematik gostermek
4. Vendor datasheet import katmanini gercek trim/set-pressure/nameplate verisiyle doldurmak
5. Yeni kapsam icin regression ve release almak
