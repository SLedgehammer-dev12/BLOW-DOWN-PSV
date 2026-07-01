from __future__ import annotations


APP_NAME = "Blowdown Studio"
APP_VERSION = "v2.4.2"
SOFTWARE_VERSION = f"{APP_NAME} {APP_VERSION}"
RELEASE_DATE_DISPLAY = "13 Nisan 2026"


RELEASE_HISTORY: list[tuple[str, str, list[str]]] = [
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
