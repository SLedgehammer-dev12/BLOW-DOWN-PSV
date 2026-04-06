# Standard Alignment Roadmap

Bu belge, mevcut `Blowdown Studio` uygulamasini API 520, API 521 ve ASME BPVC Section VIII / Section XIII beklentilerine daha yakin hale getirmek icin izlenecek teknik sirayi ozetler.

## Bu turda tamamlananlar

1. PSV tarafi `preliminary sizing` olarak ayrildi.
   - Dosya: `psv_preliminary.py`
   - Set pressure, allowable overpressure ve atmosfer basincindan relieving pressure kuruluyor.
   - Kritik ve subkritik gaz/vapor denklemleri ayrildi.
   - Conventional, balanced bellows ve pilot-operated akislar ayrildi.

2. Arayuzde PSV ve blowdown girisleri ayrildi.
   - Dosya: `blowdown_studio.py`
   - PSV modunda `MAWP / Dizayn Basinci`, `Allowable Overpressure (%)`, `PRV Tasarim Tipi`, `Upstream Rupture Disk` alanlari eklendi.
   - Blowdown modunda `Yerel Cozucu` ve `HydDown` secimleri eklendi.

3. HydDown ikinci motor olarak baglandi.
   - Dosya: `hyddown_adapter.py`
   - Mevcut arayuz girdileri HydDown giris semasina donusturuluyor.
   - Boyutlandirma ve transient simulasyon sonuclari ana uygulamaya ortak formatta donuyor.

4. PSV vendor veri modeli resmi screening kataloga baglandi.
   - Dosyalar: `psv_vendor_catalog.py`, `vendor_data/psv_vendor_catalog_official.json`
   - Varsayilan loader artik Farris, Consolidated, LESER ve kismen Flow Safe resmi katalog verilerini kullaniyor.
   - Actual area, actual-area gas coefficient ve secili balanced-bellows Kb egrileri veri setine eklendi.
   - Vendor modeli explicit size labels ile API 526 disi screening kayitlarini da tasiyabiliyor.
   - Built-in sample katalog fallback olarak korunuyor.

## Kalan teknik bosluklar

1. Final PSV selection zinciri
   - Gereken is: screening katalog yerine trim-ozel vendor datasheet import akislarini eklemek.
   - Gereken is: ASME mark ve Section XIII belge/sertifika dogrulama adimini eklemek.
   - Gereken is: exact vendor capacity tablolarini ve set-pressure-specific certified capacity lookup mantigini eklemek.

2. Vana-tipine ozgu backpressure mantigi
   - Gereken is: manufacturer-specific Kb eğrilerinde overpressure basis farklarini veri modeli olarak tasimak.
   - Gereken is: LESER `pa0/p0` bazli backpressure egrisini dogrudan cozen mantigi eklemek.
   - Gereken is: API 520-1 Figure 37 alternatif yontemini opsiyonel hale getirmek.

3. Rupture disk ve kombine cihazlar
   - Gereken is: `Kc` seciminde kullanici girisi yerine cihaz kombinasyon tablosu veya vendor datasheet akisi kullanmak.

4. API 520-2 discharge piping
   - Gereken is: reaksiyon kuvveti hesabini outlet-condition temelli gercek API 520-2 yaklasimina tasimak.
   - Gereken is: inlet pressure drop ve built-up backpressure hesaplarini ayri moduller yapmak.

5. API 521 acoustic / AIV
   - Gereken is: Mach screening yerine sound power ve acoustic fatigue screening yaklasimi eklemek.

6. Iki-faz ve cok bilesenli blowdown
   - Gereken is: mevcut yerel cozucudeki zorunlu tek-faz gaz varsayimini kaldirmak.
   - Gereken is: HydDown ve/veya ayri bir EOS tabanli cozumle kondensasyon ve flashing takibi yapmak.

7. Dagitilmis boru hatti transient modeli
   - Gereken is: uzun pipeline vakalarinda tek-hacim yaklasimi yerine segmentli line-pack / friction / wave-propagation yaklasimi eklemek.

8. Standart ve vendor benchmarklari ile dogrulama
   - Gereken is: API 520 ornekleri, vendor datasheet ornekleri ve sirket ici benchmark vakalari ile regresyon test paketi kurmak.

## Onerilen sonraki sira

1. Exact vendor import akislarini ekle.
2. API 520-2 inlet/outlet piping modulunu ayir.
3. Acoustic/AIV screening modulunu ekle.
4. Yerel cozucude iki-faz sinir kontrolu ve dusuk sicaklik uyarilarini guclendir.
5. Pipeline icin ayri transient solver karari ver: gelistirme mi, ucuncu parti entegrasyon mu.

## HydDown entegrasyon notu

- Yerel ortamda `cerberus` bagimliligi eksikti; entegrasyon testi icin kuruldu.
- Baska makinede HydDown kullanilacaksa `cerberus`, `scipy`, `tqdm`, `CoolProp`, `numpy`, `pandas` bagimliliklari dogrulanmalidir.

## Surumleme ve guncelleme uyumlulugu

- Eski surumler GitHub `latest release` etiketini okuyup yalniz surum numarasini karsilastirir; urun adinin `Blowdown Studio` olarak degismesi bunu bozmaz.
- Eski surumler indirilecek dosyayi release icindeki ilk `.exe` asset uzerinden secer. Bu nedenle release basina tek ana `.exe` asset birakmak en guvenli yontemdir.
- Yeni surumde asset secimi hem `Blowdown Studio` hem eski `Blow Down PSV` adlarini taniyacak sekilde genisletildi.
