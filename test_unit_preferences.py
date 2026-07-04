from unit_preferences import (
    DEFAULT_UNIT_PREFS,
    VALID_UNITS,
    format_area,
    format_length,
    format_mass_flow,
    format_power,
    format_pressure,
    format_sound_level,
    format_temperature,
    format_time,
    format_velocity,
    format_vol_flow,
)


class _FakeConverter:
    @staticmethod
    def convert_pressure_from_pa(value_pa, unit_str):
        return value_pa / 1e5

    @staticmethod
    def convert_mass(value_kg, unit_str):
        return value_kg


FAKE = _FakeConverter()


def test_format_temperature_celsius():
    result = format_temperature(338.15, "C")
    assert result == "65.00 °C"


def test_format_temperature_fahrenheit():
    result = format_temperature(338.15, "F")
    assert result == "149.00 °F"


def test_format_temperature_kelvin():
    result = format_temperature(338.15, "K")
    assert result == "338.15 K"


def test_format_temperature_freezing():
    result = format_temperature(273.15, "C")
    assert result == "0.00 °C"


def test_format_velocity_m_s():
    result = format_velocity(100.0, "m/s")
    assert result == "100.00 m/s"


def test_format_velocity_ft_s():
    result = format_velocity(100.0, "ft/s")
    assert result.endswith("ft/s")
    val = float(result.split()[0])
    assert abs(val - 328.08) < 0.01


def test_format_power_kw():
    result = format_power(1e6, "kW")
    assert result == "1000.00 kW"


def test_format_power_mw():
    result = format_power(5e6, "MW")
    assert result == "5.000 MW"


def test_format_power_hp():
    result = format_power(74570.0, "HP")
    assert result.endswith("HP")
    val = float(result.split()[0])
    assert abs(val - 100.0) < 0.1


def test_format_power_btu_s():
    result = format_power(10550.6, "BTU/s")
    assert result.endswith("BTU/s")


def test_format_sound_level():
    result = format_sound_level(139.6, "dB")
    assert result == "139.6 dB ref 1pW"


def test_default_unit_prefs_all_keys_have_valid_units():
    for key, default in DEFAULT_UNIT_PREFS.items():
        assert key in VALID_UNITS, f"{key} VALID_UNITS'te eksik"
        assert default in VALID_UNITS[key], f"{key} varsayilani {default} VALID_UNITS'te yok"


def test_format_pressure_with_converter():
    result = format_pressure(75e5, "barg", FAKE)
    assert "barg" in result
    val = float(result.split()[0])
    assert abs(val - 75.0) < 0.001


def test_format_time_minutes():
    result = format_time(120.0, "min")
    assert "2.0 min" in result


def test_format_time_seconds():
    result = format_time(120.0, "s")
    assert "120.0 s" in result


def test_format_mass_flow_kg_h():
    result = format_mass_flow(1000.0, "kg/h", FAKE)
    assert "kg/h" in result


def test_format_mass_flow_lb_h():
    result = format_mass_flow(1000.0, "lb/h", FAKE)
    assert "lb/h" in result


def test_format_vol_flow_m3_h():
    result = format_vol_flow(100.0, "m3/h")
    assert "m3/h" in result


def test_format_area_mm2():
    result = format_area(0.001, "mm2")
    assert "mm2" in result


def test_format_length_mm():
    result = format_length(1.0, "mm")
    assert "1000 mm" in result


if __name__ == "__main__":
    test_format_temperature_celsius()
    test_format_temperature_fahrenheit()
    test_format_temperature_kelvin()
    test_format_temperature_freezing()
    test_format_velocity_m_s()
    test_format_velocity_ft_s()
    test_format_power_kw()
    test_format_power_mw()
    test_format_power_hp()
    test_format_power_btu_s()
    test_format_sound_level()
    test_default_unit_prefs_all_keys_have_valid_units()
    test_format_pressure_with_converter()
    test_format_time_minutes()
    test_format_time_seconds()
    test_format_mass_flow_kg_h()
    test_format_mass_flow_lb_h()
    test_format_vol_flow_m3_h()
    test_format_area_mm2()
    test_format_length_mm()
    print("ALL TEST_UNIT_PREFERENCES PASSED")
