"""Unit tests for ChemAgent tools. Run with: pytest tests/"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from src.tools.molecular import molecular_weight, molecular_properties, name_to_smiles
from src.tools.thermo import antoine_vapor_pressure, ideal_gas_volume
from src.tools.python_exec import python_exec


class TestMolecular:
    def test_molecular_weight_water(self):
        result = molecular_weight("O")
        assert abs(result["molecular_weight_g_per_mol"] - 18.015) < 0.05

    def test_molecular_weight_ethanol(self):
        result = molecular_weight("CCO")
        assert abs(result["molecular_weight_g_per_mol"] - 46.07) < 0.1

    def test_molecular_weight_aspirin(self):
        result = molecular_weight("CC(=O)Oc1ccccc1C(=O)O")
        assert abs(result["molecular_weight_g_per_mol"] - 180.16) < 0.2

    def test_molecular_weight_invalid_smiles(self):
        with pytest.raises(ValueError):
            molecular_weight("not-a-smiles")

    def test_molecular_properties_returns_logp(self):
        result = molecular_properties("CCO")
        assert "logP" in result
        assert "tpsa" in result

    def test_name_to_smiles_known(self):
        result = name_to_smiles("ethanol")
        assert result["smiles"] == "CCO"

    def test_name_to_smiles_case_insensitive(self):
        result = name_to_smiles("  Ethanol  ")
        assert result["smiles"] == "CCO"

    def test_name_to_smiles_unknown(self):
        result = name_to_smiles("unobtainium")
        assert "error" in result


class TestThermo:
    def test_antoine_water_100c_near_1_atm(self):
        # water at 100 C should give ~101.3 kPa
        result = antoine_vapor_pressure("water", 100)
        assert 95 < result["vapor_pressure_kpa"] < 108

    def test_antoine_ethanol_50c(self):
        result = antoine_vapor_pressure("ethanol", 50)
        # literature: ~29.5 kPa
        assert 25 < result["vapor_pressure_kpa"] < 34

    def test_antoine_unknown_compound(self):
        result = antoine_vapor_pressure("unobtainium", 100)
        assert "error" in result

    def test_ideal_gas_stp(self):
        # 1 mol at 273.15 K, 101.325 kPa → 22.4 L
        result = ideal_gas_volume(1, 273.15, 101.325)
        assert 22 < result["volume_l"] < 23

    def test_ideal_gas_invalid(self):
        result = ideal_gas_volume(-1, 300, 100)
        assert "error" in result


class TestPythonExec:
    def test_simple_calc(self):
        result = python_exec("print(2 + 2)")
        assert result["stdout"] == "4"

    def test_math_module(self):
        result = python_exec("import math\nprint(round(math.pi, 3))")
        assert result["stdout"] == "3.142"

    def test_disallowed_import_blocked(self):
        result = python_exec("import os\nprint(os.getcwd())")
        assert "error" in result

    def test_no_print_warning(self):
        result = python_exec("x = 5")
        assert "warning" in result

    def test_syntax_error_returns_error(self):
        result = python_exec("def (")
        assert "error" in result
