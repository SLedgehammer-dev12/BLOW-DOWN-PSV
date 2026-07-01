import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from methodology_content import build_methodology_text


def test_build_methodology_text_contains_sections():
    text = build_methodology_text(
        native_engine_name="Yerel Çözücü",
        segmented_engine_name="Segmented Pipeline",
        two_phase_engine_name="Two-Phase Screening",
    )
    assert "API 520" in text
    assert "API 521" in text
    assert "API 2000" in text
    assert "CoolProp" in text
    assert "Yerel Çözücü" in text


if __name__ == "__main__":
    test_build_methodology_text_contains_sections()
    print("TEST COMPLETED")
