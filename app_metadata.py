from __future__ import annotations


APP_NAME = "Blowdown Studio"
APP_VERSION = "v2.4.8"
SOFTWARE_VERSION = f"{APP_NAME} {APP_VERSION}"
RELEASE_DATE_DISPLAY = "5 Temmuz 2026"


RELEASE_HISTORY: list[tuple[str, str, list[str]]] = [
    (
        "v2.4.8",
        "5 Temmuz 2026",
        [
            "Sicaklik format duzeltmesi: Kelvin'den °C/F donusumu dogru yapiliyor (611°C hatasi giderildi).",
            "Vana sayisi/direk sayisi alanlarinda 0 degeri dogru isleniyor (or→is None duzeltmesi).",
            "Hiz (m/s/ft/s), guc (kW/MW/HP/BTU/s), ses seviyesi (dB) birim secenekleri eklendi.",
            "Akustik/deşarj piping rapor satirlari secilen birimlere gore dinamik hale getirildi.",
        ],
    ),
    (
        "v2.4.7",
        "4 Temmuz 2026",
        [
            "Deşarj Boru Hattı (API 521) girdi alanlari eklendi: boru uzunlugu, ic cap, dirsek/te/vana sayilari, puruzluluk.",
            "Kullanici boru hatti parametrelerini dogrudan girebilir; bos birakilan alanlar varsayilan degerleri kullanir.",
            "Raporda puruzluluk ve fittings detaylari ayrica gosterilir.",
            "HydDown numpy.testing import hatasi giderildi (build.spec).",
        ],
    ),
    (
        "v2.4.6",
        "3 Temmuz 2026",
        [
            "Plug Vana (Blowdown) vana tipi eklendi; Cd varsayilani 0.80.",
            "Birim tercihleri dialogu eklendi; basinc, sicaklik, kutle, debi ve hacimsel akis birimleri kullanici tarafindan secilebilir.",
            "Rapor ve grafik eksen etiketleri secilen birimlere gore dinamik olarak guncellenir.",
            "Birim tercihleri settings dosyasina kaydedilip geri yuklenir.",
        ],
    ),
    (
        "v2.4.5",
        "2 Temmuz 2026",
        [
            "Modern arayuz temalari eklendi: Modern Acik, Modern Koyu ve Performans (varsayilan) modlari.",
            "Her girdi alani icin bilgilendirici tooltip (ⓘ ikonu) eklendi; fareyle uzerine gelindiginde muhendislik aciklamasi gosterilir.",
            "Gorunum menusu eklendi; tema gecisi anlik olarak uygulanir.",
            "UI widget stil konfigurasyonu eklendi (ttk.Style, tema paletleri, sistem font tespiti).",
        ],
    ),
    (
        "v2.4.4",
        "2 Temmuz 2026",
        [
            "GitHub Actions CI/CD eklendi: tag push'landiginda Windows .exe otomatik build edilip release'e yuklenir.",
            "build.spec ile dinamik versiyon okuma; her surum icin ayri spec dosyasi gerekmez.",
            "Eski sabit-surum spec dosyalari temizlendi.",
        ],
    ),
    (
        "v2.4.3",
        "2 Temmuz 2026",
        [
            "Blowdown Analizi sekmesine yatay ve dikey scrollbar eklendi; farkli cozunurluklerde kaydirma destegi saglandi.",
            "Ana ayarlar ve gaz kompozisyonu arasina PanedWindow eklenerek kolonlar kullanici tarafindan boyutlandirabilir hale getirildi.",
            "Mod degisikligi sonrasi scroll bolgesi otomatik guncellenerek Temel Girdiler altindaki input kutularinin gorunurlugu saglandi.",
            "macOS trackpad ve Linux fare tekerleği uyumlulugu eklendi; Shift+faret tekerleği ile yatay kaydirma destegi saglandi.",
            "GitHub guncelleme kontrolu draft ve prerelease surumlerini filtreleyecek sekilde iyilestirildi.",
            "UI degisikliklerini kapsayan 7 yeni test eklendi.",
        ],
    ),
    (
        "v2.4.2",
        "13 Nisan 2026",
        [
            "Steam ve Liquid servisleri icin opsiyonel psvpy cross-check eklendi; native API 520 sizing motoru ana hesap kaynagi olarak korundu.",
            "PSV raporuna psvpy provider, gerekli alan ve native sizing farki ayri bolum olarak yazdiriliyor.",
            "PSV ayarlarina psvpy cross-check secenegi eklendi ve bu tercih settings dosyasina kaydedilir hale getirildi.",
            "MIT lisansli psvpy altkumesi third_party altinda izole vendor yapisiyla eklendi.",
            "Tk/Tcl eksikligi olan ortamlarda UI testleri temiz skip verecek sekilde sertlestirildi.",
        ],
    ),
    (
        "v2.4.1",
        "9 Nisan 2026",
        [
            "Paketleme sadeleştirildi; gereksiz test, notebook ve opsiyonel backend yukleri exe disina alindi.",
            "Windows version metadata eklendi ve release build yeniden uretildi.",
        ],
    ),
    (
        "v2.4.0",
        "9 Nisan 2026",
        [
            "Ana arayuz oranlari yeniden duzenlendi ve vana sayisi alanlari tekrar gorunur hale getirildi.",
            "PSV sizing akisinda kullanicinin sectigi vana sayisina gore vana basina gerekli alan ve uygun vana secimi eklendi.",
        ],
    ),
    (
        "v2.3.1",
        "6 Nisan 2026",
        [
            "HydDown paketli exe import yolu duzeltildi.",
            "Blowdown ve PSV grafik seti onceki beklenen kapsama geri getirildi.",
            "Updater'in hotfix surumunu gorebilmesi icin yeni tag duzeni uygulandi.",
        ],
    ),
]


def build_about_text(*, app_name: str = APP_NAME, app_version: str = APP_VERSION) -> str:
    title = f"{app_name} HAKKINDA"
    lines = [
        title,
        "=" * len(title),
        "",
        f"Urun adi       : {app_name}",
        f"Surum          : {app_version}",
        f"Yayin tarihi   : {RELEASE_DATE_DISPLAY}",
        "",
        "Kapsam",
        "------",
        "Bu uygulama API 520 PSV on boyutlandirma, API 521 blowdown/depressuring ve API 2000 tank havalandirma screening is akislari icin hazirlanmis bir proses guvenligi aracidir.",
        "CoolProp tabanli termofiziksel ozellikler, vendor screening ve raporlama/export akislari tek masaustu arayuzunde birlestirilir.",
        "",
        "Guncelleme Tarihcesi",
        "--------------------",
    ]

    for version, release_date, bullets in RELEASE_HISTORY:
        lines.append(f"{version} - {release_date}")
        for bullet in bullets:
            lines.append(f"- {bullet}")
        lines.append("")

    lines.extend(
        [
            "Not",
            "---",
            "Built-in vendor ve screening sonuclari muhendislik yardimcisi niteligindedir; final secim ve uyumluluk onayi icin vendor datasheet, ilgili API standardi ve yetkili muhendis dogrulamasi ayrica gereklidir.",
        ]
    )
    return "\n".join(lines)
