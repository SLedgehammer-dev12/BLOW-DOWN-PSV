# Blowdown Studio - Proje Durum Raporu

Bu belge, yazılımın gelişim sürecini, tamamlanan özellikleri ve gelecek planlarını içerir.

## Aktif Durum

- Ürün adı: `Blowdown Studio`
- Aktif giriş dosyası: `blowdown_studio.py`
- Geriye dönük uyumluluk başlatıcısı: `Blow Down PSV V3.py`
- Eski sürüm snapshot'ları: `legacy/`

## Tamamlanan Sürümler ve Değişiklikler

### v2.3
- **Adlandırma Ayrıştırması:** Ürün adı, yerel çözücü adı ve sürüm etiketi birbirinden ayrıldı.
- **Motor Seçimi:** `Yerel Çözücü` ve `HydDown` aynı arayüzden seçilebilir hale geldi.
- **PSV Ön Boyutlandırma:** API 520-1 tabanlı preliminary sizing akışı ayrıldı.
- **Arşivleme:** Eski sürüm dosyaları `legacy/` klasörüne taşındı.

### v2.1
- **Kütle Doğrulama (Mass Verification):** EOS (CoolProp) tabanlı hassas kütle ile İdeal Gaz denklemi arasındaki farkın raporlanması sağlandı.
- **Simülasyon Hassasiyeti:** Simülasyon başlangıç kütlesi doğrudan `rho * V` üzerinden başlatılarak %100 fiziksel tutarlılık sağlandı.
- **Mach Sayısı Düzeltmesi:** Vana boğazındaki hız 1.0 Mach ile sınırlandırıldı (Choked Flow). Çıkış hattı hızı nominal çap ve isentalpik genleşme verileriyle gerçeğe yakın modellendi.

### v2.0
- **Mühendislik Raporu:** Raporlar API 520/521 standartlarına uygun hale getirildi.
- **İleri Termodinamik:** Entalpi (H), Entropi (S) ve Ses Hızı (c) hesaplamaları eklendi.
- **Veri Dışa Aktarma:** Simülasyon sonuçlarının `.csv` olarak dışa aktarılması sağlandı.
- **Metodoloji:** Yardım penceresine API formül yapıları eklendi.

### v1.x Serisi
- **Motor:** Blowdown (depressurisation) ve PSV Sizing motorlarının birleştirilmesi.
- **Isı Transferi:** Boru-Gaz arası ısı transferi analizi (Nusselt/Grashof).

---

## Gelecek Planları ve Öneriler

1. **PDF Rapor Çıktısı:** Mevcut metin raporun profesyonel, logolu bir PDF dosyasına dönüştürülmesi.
2. **2-Phase Flow (İki Fazlı Akış):** API 520 Part I, Ek D kapsamında (HEM yöntemi) sıvı+gaz karışımları için PSV boyutlandırma desteği.
3. **Grafiksel UI Yenileme:** Matplotlib grafiklerinin daha interaktif hale getirilmesi (Zoom/Pan özellikleri).
4. **Vana Veritabanı Genişletme:** Daha fazla marka ve model (Masoneilan, Anderson Greenwood vb.) verisinin eklenmesi.

---
*Son Güncelleme: 6 Nisan 2026*
