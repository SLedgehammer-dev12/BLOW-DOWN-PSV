import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from materials import carbon_steel_cp_j_kgk


def test_carbon_steel_cp_is_temperature_dependent():
    cp_200 = carbon_steel_cp_j_kgk(200.0)
    cp_300 = carbon_steel_cp_j_kgk(300.0)
    cp_500 = carbon_steel_cp_j_kgk(500.0)

    assert cp_200 < cp_300 < cp_500
    assert 350.0 <= cp_200 <= 410.0
    assert 450.0 <= cp_300 <= 490.0
    assert 580.0 <= cp_500 <= 630.0


if __name__ == "__main__":
    test_carbon_steel_cp_is_temperature_dependent()
    print("TEST COMPLETED")
