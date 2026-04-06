# Blowdown Studio - Proje Durum Raporu

Bu belge, yazilimin gelisim surecini, tamamlanan ozellikleri ve gelecek planlarini icerir.

## Aktif Durum

- Urun adi: `Blowdown Studio`
- Aktif giris dosyasi: `blowdown_studio.py`
- Geriye donuk uyumluluk baslaticisi: `Blow Down PSV V3.py`
- Eski surum snapshot'lari: `legacy/`

## Tamamlanan Surumler ve Degisiklikler

### v2.3.1
- **Hotfix Release:** `v2.3` altinda asset degistirme yerine yeni tag kullanilarak updater uyumlulugu geri getirildi.
- **HydDown Paketleme Duzeltmesi:** Paketli `.exe` icinde `hyddown` import ve bagimlilik yolu duzeltildi.
- **Grafiklerin Geri Yuklenmesi:** Blowdown ve PSV tarafinda onceki genis grafik seti geri getirildi.

### v2.3
- **Adlandirma Ayrismasi:** Urun adi, yerel cozucu adi ve surum etiketi birbirinden ayrildi.
- **Motor Secimi:** `Yerel Cozucu` ve `HydDown` ayni arayuzden secilebilir hale geldi.
- **PSV On Boyutlandirma:** API 520-1 tabanli preliminary sizing akis ayri bir moduler yapiya tasindi.
- **Arsivleme:** Eski surum dosyalari `legacy/` klasorune tasindi.

### v2.1
- **Kutle Dogrulama:** EOS tabanli hassas kutle ile ideal gaz hesaplari arasindaki fark raporlanabilir hale geldi.
- **Simulasyon Hassasiyeti:** Baslangic kutlesi dogrudan `rho * V` uzerinden alinacak sekilde duzeltildi.
- **Mach Sayisi Duzeltmesi:** Bogaz ve cikis hizlarinda bozulmaya yol acan onceki basitlestirmeler temizlendi.

### v2.0
- **Muhendislik Raporu:** Rapor dili API 520/521 baglaminda daha duzenli hale getirildi.
- **Ileri Termodinamik:** Entalpi, entropi ve ses hizi hesaplari eklendi.
- **Veri Disa Aktarma:** Simulasyon sonuclari `.csv` olarak kaydedilebilir hale getirildi.
- **Metodoloji:** Yardim penceresine formuller ve metodoloji notlari eklendi.

### v1.x Serisi
- **Motor:** Blowdown ve PSV sizing motorlari ayni uygulamada birlestirildi.
- **Isi Transferi:** Boru-gaz isi transferi analizi eklendi.

## Gelecek Planlari ve Oneriler

1. **PDF Rapor Ciktisi:** Mevcut metin raporun profesyonel bir PDF ciktisina donusturulmesi.
2. **2-Phase Flow:** API 520 Part I kapsaminda iki fazli sizing destegi.
3. **Grafiksel UI Yenileme:** Matplotlib grafiklerinin daha interaktif hale getirilmesi.
4. **Vana Veritabani Genisletme:** Daha fazla marka ve model verisinin eklenmesi.

*Son Guncelleme: 7 Nisan 2026*
