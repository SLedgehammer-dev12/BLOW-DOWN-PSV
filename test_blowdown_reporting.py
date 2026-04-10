from pathlib import Path
from tempfile import TemporaryDirectory

from blowdown_reporting import BlowdownReportBundle, export_blowdown_report_csv, export_blowdown_report_pdf


def test_blowdown_report_exports():
    bundle = BlowdownReportBundle(
        title="Blowdown Analiz Raporu",
        text="Satır 1\nSatır 2\n",
        summary_rows=[("Sonuç", "PASS"), ("Gerçekleşen Süre (s)", "10.0")],
        generated_on="10.04.2026",
        software_version="Blowdown Studio v2.3.1",
    )

    with TemporaryDirectory() as tmp_dir:
        csv_path = Path(tmp_dir) / "blowdown_report.csv"
        pdf_path = Path(tmp_dir) / "blowdown_report.pdf"
        export_blowdown_report_csv(csv_path, bundle)
        export_blowdown_report_pdf(pdf_path, bundle)
        assert csv_path.exists() and csv_path.stat().st_size > 0
        assert pdf_path.exists() and pdf_path.stat().st_size > 0


if __name__ == "__main__":
    test_blowdown_report_exports()
    print("TEST COMPLETED")
