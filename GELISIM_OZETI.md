# Blowdown Studio - Gelisim Ozeti

## Mevcut durum

0. Aktif surum `v2.4.4`.
1. Aktif uygulama adi `Blowdown Studio` olarak standardize edildi.
2. Aktif giris dosyasi `blowdown_studio.py` oldu.
3. `Blow Down PSV V3.py` yalniz geriye donuk uyumluluk baslaticisi olarak birakildi.
4. Yerel blowdown motoru arayuzde `Yerel Cozucu` adiyla gosteriliyor.
5. HydDown ikinci hesap motoru olarak entegre edildi.
6. Eski surum dosyalari `legacy/` klasorune tasindi.
7. PSV tarafinda `actual area`, `certified gas Kd` ve `Kb curve` iceren vendor veri modeli eklendi.
8. Varsayilan PSV katalogu resmi screening verileri yukluyor.
9. Vendor modeli API 526 harfleri disindaki vendor size etiketlerini de tasiyabiliyor.

## Aktif teknik dosyalar

- Ana uygulama: `blowdown_studio.py`
- PSV preliminary sizing: `psv_preliminary.py`
- PSV vendor katalog modeli: `psv_vendor_catalog.py`
- Resmi vendor screening veri seti: `vendor_data/psv_vendor_catalog_official.json`
- Vendor kaynak notlari: `vendor_data/README.md`
- HydDown adaptoru: `hyddown_adapter.py`
- Paketleme: `build.spec` (dinamik versiyon okuma)

## v2.4.4

- GitHub Actions CI/CD eklendi: tag push'landiginda Windows .exe otomatik build edilip release'e yuklenir.
- `build.spec` ile dinamik versiyon okuma — her surum icin ayri spec dosyasi gerekmez.
- Eski sabit-surum spec dosyalari temizlendi.
- Release yetkilendirme duzeltmesi (permissions: contents: write).

## v2.4.3

- Blowdown Analizi sekmesine yatay ve dikey scrollbar eklendi; farkli cozunurluklerde kaydirma destegi saglandi.
- Ana ayarlar ve gaz kompozisyonu arasina PanedWindow eklenerek kolonlar kullanici tarafindan boyutlandirabilir hale getirildi.
- macOS trackpad ve Linux fare tekerlegi uyumlulugu eklendi.
- GitHub guncelleme kontrolu draft ve prerelease surumlerini filtreleyecek sekilde iyilestirildi.
- **Hata duzeltmesi:** Buyuk blowdown alanlarinda kütle clamp bug'i giderildi (bisection ilk adimda crash oluyordu).
- **Hata duzeltmesi:** API 521 fire case isi girdisi native enerji dengesine eklendi.
- **Yeni motor: DCMR Rijnmond (Analitik)** — Hollanda DCMR otoritesi tarafindan yayinlanan kapali-formul blowdown hesaplama yontemi eklendi. Adyabatik-izentropik, surekli choked akis kabuluyle anlik (iterasyonsuz) sonuc uretir. VR (Veiligheidsrapport) basvurulari icin referans yontem.
- Two-phase motorunda sicakliga bagli celik Cp modeli (carbon_steel_cp_j_kgk) kullanima alindi.

## v2.4.2

- Steam ve Liquid servisleri icin opsiyonel `psvpy` cross-check eklendi; native API 520 sizing sonucu ana hesap olarak korundu.
- PSV raporuna `psvpy` kaynak, gerekli alan ve native sizing farki ayri bolum olarak eklendi.
- `Hakkinda / Guncelleme Tarihcesi` penceresi yardim menusune eklendi.
- Ayarlara `psvpy cross-check` tercihi kaydedilir hale getirildi.
- Tk/Tcl eksikligi olan ortamlarda UI testleri temiz skip verecek sekilde guclendirildi.

## v2.4.1

- Paketleme sadeleştirildi; gereksiz test/notebook/backend yükleri dışarı alındı.
- Windows version metadata eklendi ve release build yeniden üretildi.

## v2.4.0

- Default ana arayuz genislikleri `Temel Girdiler` `%35`, `Gaz Kompozisyonu` `%15` ve `Analiz Raporu` `%50` olacak sekilde guncellendi.
- Blowdown ve PSV modlarinda `Vana Sayisi` alani yeniden gorunur hale getirildi.
- PSV sizing akisinda kullanicinin sectigi vana sayisi uzerinden vana basina gerekli alan hesaplanip uygun vana boyutu seciliyor.

## Testler

- `test_psv_sizing.py`
- `test_api520_preliminary.py`
- `test_psv_vendor_catalog.py`
- `test_native_blowdown_api521.py`
- `test_dcmr_engine.py`
- `test_hyddown_adapter.py`
- `test_ui_builders.py`
- `test_ui_state_actions.py`
- `test_update_actions.py`
- `test_update_flow_actions.py`
- `test_blowdown_workflow.py`
- `test_app_metadata.py`
- `test_ui_mode_logic.py`

## Not

Release yayinlarken tek ana `.exe` asset birakilmasi onerilir. Boylece hem eski surumler hem yeni surumler guncellemeyi dogru dosyadan indirebilir.

## v2.3.1 hotfix

- Paketli exe icinde HydDown import yolu duzeltildi.
- Blowdown ve PSV grafik seti onceki beklenen kapsam seviyesine geri getirildi.
- Yeni tag kullanilarak updater'in `v2.3`ten bu hotfix'i gorebilmesi saglandi.
