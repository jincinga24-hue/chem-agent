"""Unit tests for the fluids tool. Run with: pytest tests/test_fluids.py"""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src.tools.fluids import (
    water_properties,
    pipe_roughness,
    standard_pipe_id,
    fitting_k,
    reynolds_number,
    friction_factor_colebrook,
    friction_factor_swamee_jain,
    solve_three_reservoir_network,
)


class TestWaterProperties:
    def test_20c_matches_iapws(self):
        r = water_properties(20.0)
        assert abs(r["density_kg_m3"] - 998.2) < 0.5
        # IAPWS viscosity at 20 C = 1.0016e-3 Pa.s
        assert abs(r["viscosity_pa_s"] - 1.002e-3) < 0.01e-3

    def test_4c_density_maximum(self):
        # Water density peaks at ~4 C near 1000 kg/m^3
        r = water_properties(4.0)
        assert 999.9 < r["density_kg_m3"] < 1000.1

    def test_source_present(self):
        r = water_properties(25.0)
        assert "source" in r
        assert "density" in r["source"]
        assert "viscosity" in r["source"]

    def test_out_of_range(self):
        assert "error" in water_properties(-5)
        assert "error" in water_properties(150)


class TestPipeRoughness:
    def test_commercial_steel_moody(self):
        r = pipe_roughness("commercial_steel")
        assert r["roughness_mm"] == 0.046
        assert "Moody" in r["source"]["citation"]

    def test_hdpe_australian_standard(self):
        r = pipe_roughness("hdpe")
        assert "4130" in r["source"]["citation"]

    def test_case_insensitive(self):
        r = pipe_roughness("  COMMERCIAL-Steel ")
        assert r["roughness_mm"] == 0.046

    def test_unknown(self):
        assert "error" in pipe_roughness("unobtainium")


class TestStandardPipeID:
    def test_steel_dn100_sch40(self):
        # ASME B36.10M DN100 Sch40: ID ~ 102.26 mm
        r = standard_pipe_id("steel_sch40", 100)
        assert abs(r["inside_diameter_mm"] - 102.26) < 0.01
        assert "ASME" in r["source"]["citation"]

    def test_hdpe_dn90_pn16(self):
        r = standard_pipe_id("hdpe_pn16", 90)
        assert abs(r["inside_diameter_mm"] - 73.6) < 0.01

    def test_unknown_standard(self):
        assert "error" in standard_pipe_id("unicorn", 100)

    def test_unknown_size(self):
        assert "error" in standard_pipe_id("steel_sch40", 99)


class TestFittingK:
    def test_90_elbow_crane(self):
        r = fitting_k("elbow_90_standard")
        assert r["K"] == 0.75
        assert "Crane" in r["source"]["citation"]

    def test_globe_valve_high_loss(self):
        # Globe valves have K ~ 10 per Crane TP-410
        r = fitting_k("globe_valve_open")
        assert r["K"] >= 5.0


class TestFrictionFactor:
    def test_laminar_regime(self):
        r = friction_factor_colebrook(1000, 0.0001, 0.05)
        assert abs(r["friction_factor"] - 64.0 / 1000) < 1e-6
        assert r["regime"] == "laminar"

    def test_turbulent_matches_moody_chart(self):
        # Commercial steel, D=0.1 m, Re=1e5, eps/D=4.6e-4.
        # Colebrook closed-form gives f ~ 0.0202; Moody chart readings for
        # this regime fall in the 0.020-0.022 band.
        r = friction_factor_colebrook(1e5, 0.046e-3, 0.1)
        assert 0.019 < r["friction_factor"] < 0.023
        assert r["regime"] == "turbulent"

    def test_swamee_jain_close_to_colebrook(self):
        # Swamee-Jain within ~1% of Colebrook in valid range
        sj = friction_factor_swamee_jain(1e5, 0.046e-3, 0.1)
        cw = friction_factor_colebrook(1e5, 0.046e-3, 0.1)
        rel_err = abs(sj["friction_factor"] - cw["friction_factor"]) / cw["friction_factor"]
        assert rel_err < 0.01

    def test_smooth_pipe_turbulent(self):
        # Smooth pipe at Re=1e5: Blasius gives f = 0.3164/Re^0.25 = 0.01779
        r = friction_factor_colebrook(1e5, 0.0, 0.1)
        assert abs(r["friction_factor"] - 0.0180) < 0.0005


class TestReynolds:
    def test_laminar_classification(self):
        r = reynolds_number(1000, 0.01, 0.1, 1e-3)
        assert r["regime"] == "laminar"

    def test_turbulent_classification(self):
        r = reynolds_number(1000, 2.0, 0.1, 1e-3)
        assert r["regime"] == "turbulent"
        assert abs(r["reynolds_number"] - 200000) < 1


class TestThreeReservoirNetwork:
    """Regression test on the ENGR30002 assignment benchmark case."""

    def _benchmark_inputs(self):
        wp = water_properties(20.0)
        pipes = [
            {
                "P_pa": 500_000.0, "z_surface_m": 60.0, "length_m": 100.0,
                "diameter_m": 0.10226, "roughness_m": 0.046e-3,
                "sum_K": 0.5 + 1.0 + 2 * 0.75 + 0.15,
            },
            {
                "P_pa": 200_000.0, "z_surface_m": 25.0, "length_m": 150.0,
                "diameter_m": 0.0736, "roughness_m": 0.007e-3,
                "sum_K": 0.5 + 1.0 + 0.35 + 0.05,
            },
            {
                "P_pa": 101_325.0, "z_surface_m": 7.0, "length_m": 80.0,
                "diameter_m": 0.05250, "roughness_m": 0.15e-3,
                "sum_K": 0.5 + 1.0 + 0.75 + 10.0,
            },
        ]
        fluid = {
            "density_kg_m3": wp["density_kg_m3"],
            "viscosity_pa_s": wp["viscosity_pa_s"],
            "z_J_m": 2.0,
        }
        return pipes, fluid

    def test_junction_pressure_matches_expected(self):
        pipes, fluid = self._benchmark_inputs()
        r = solve_three_reservoir_network(pipes, fluid)
        assert "error" not in r
        assert abs(r["junction_pressure_kpa"] - 890.1) < 5.0

    def test_continuity_satisfied(self):
        pipes, fluid = self._benchmark_inputs()
        r = solve_three_reservoir_network(pipes, fluid)
        assert abs(r["continuity_residual_m3_s"]) < 1e-6

    def test_flow_directions_physical(self):
        # Tank 1 has highest total head (51 m pressure head + 60 m elevation),
        # so it should feed the junction; tanks 2 and 3 should receive.
        pipes, fluid = self._benchmark_inputs()
        r = solve_three_reservoir_network(pipes, fluid)
        dirs = [p["direction"] for p in r["pipes"]]
        assert dirs[0] == "tank_to_junction"
        assert dirs[1] == "junction_to_tank"
        assert dirs[2] == "junction_to_tank"

    def test_turbulent_regime_assumed(self):
        pipes, fluid = self._benchmark_inputs()
        r = solve_three_reservoir_network(pipes, fluid)
        for p in r["pipes"]:
            assert p["reynolds"] > 4000, f"pipe {p['pipe_index']} not turbulent"

    def test_wrong_pipe_count(self):
        r = solve_three_reservoir_network([{}, {}], {"z_J_m": 0, "density_kg_m3": 1, "viscosity_pa_s": 1e-3})
        assert "error" in r


class TestTorricelliBenchmark:
    """Sanity check the Q1 closed-form: L_max = h0 at the middle hole."""

    def test_middle_hole_range_equals_h0(self):
        g = 9.81
        h0 = 1.20
        ranges = []
        for frac in [0.25, 0.5, 0.75]:
            h_i = frac * h0
            V_i = math.sqrt(2 * g * (h0 - h_i))
            t_i = math.sqrt(2 * h_i / g)
            ranges.append(V_i * t_i)
        assert abs(ranges[1] - h0) < 1e-9  # middle hole
        assert ranges[1] == max(ranges)
