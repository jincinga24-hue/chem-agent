"""Unit tests for the RAFT polymerization tool."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import math
from src.tools.polymer import raft_kinetics, raft_target_dp


class TestRaftKinetics:
    def test_styrene_aibn_cdb_baseline(self):
        # Classic RAFT: styrene/AIBN/CDB at 70 C, 6 h, [M]=4M, [CTA]=0.04M, [I]=0.004M.
        # Expect: x in 0.3–0.7, DP ~ 30–80, Đ < 1.3.
        r = raft_kinetics(
            monomer="styrene",
            initiator="aibn",
            cta="cdb",
            M0=4.0,
            I0=0.004,
            CTA0=0.04,
            T_C=70,
            t_final_s=6 * 3600,
        )
        assert "error" not in r
        x = r["final"]["conversion"]
        Mn = r["final"]["Mn_g_per_mol"]
        D = r["final"]["dispersity"]
        assert 0.2 < x < 0.9, f"unexpected conversion {x}"
        assert 1000 < Mn < 12000, f"unexpected Mn {Mn}"
        assert 1.0 < D < 1.5, f"unexpected dispersity {D}"

    def test_dp_grows_linearly_with_conversion(self):
        # Hallmark of living polymerization: DP_n ∝ x. (Mn has a CTA offset.)
        r = raft_kinetics("styrene", "aibn", "cdb", 4.0, 0.004, 0.04, 70, 7200)
        xs = r["series"]["conversion"]
        DPs = r["series"]["DP_n"]
        i, j = 10, 30
        assert xs[i] > 0.01 and xs[j] > 0.01
        ratio = DPs[j] / DPs[i]
        x_ratio = xs[j] / xs[i]
        assert abs(ratio - x_ratio) / x_ratio < 0.01

    def test_unknown_monomer(self):
        r = raft_kinetics("unobtainium", "aibn", "cdb", 4, 0.004, 0.04, 70, 3600)
        assert "error" in r

    def test_unknown_cta(self):
        r = raft_kinetics("styrene", "aibn", "fake_cta", 4, 0.004, 0.04, 70, 3600)
        assert "error" in r

    def test_negative_inputs(self):
        r = raft_kinetics("styrene", "aibn", "cdb", -1, 0.004, 0.04, 70, 3600)
        assert "error" in r

    def test_higher_initiator_means_faster(self):
        slow = raft_kinetics("styrene", "aibn", "cdb", 4.0, 0.001, 0.04, 70, 3600)
        fast = raft_kinetics("styrene", "aibn", "cdb", 4.0, 0.010, 0.04, 70, 3600)
        assert fast["final"]["conversion"] > slow["final"]["conversion"]

    def test_higher_temperature_means_faster(self):
        cool = raft_kinetics("styrene", "aibn", "cdb", 4.0, 0.004, 0.04, 60, 3600)
        warm = raft_kinetics("styrene", "aibn", "cdb", 4.0, 0.004, 0.04, 80, 3600)
        assert warm["final"]["conversion"] > cool["final"]["conversion"]

    def test_lower_cta_gives_higher_dp(self):
        more_cta = raft_kinetics("styrene", "aibn", "cdb", 4.0, 0.004, 0.08, 70, 3600)
        less_cta = raft_kinetics("styrene", "aibn", "cdb", 4.0, 0.004, 0.02, 70, 3600)
        assert less_cta["final"]["DP_n"] > more_cta["final"]["DP_n"]


class TestRaftTargetDp:
    def test_target_dp_100_styrene(self):
        # M0/CTA0 = 100 => CTA0 = 0.04 mol/L if M0 = 4 mol/L
        r = raft_target_dp("styrene", "cdb", M0=4.0, target_DP=100)
        assert "error" not in r
        assert abs(r["required_CTA0_mol_L"] - 0.04) < 1e-6
        # Target Mn ~ 100 * 104.15 + 272.39 ≈ 10687 g/mol
        assert 10000 < r["target_Mn_g_per_mol"] < 11000

    def test_target_dp_unknown_monomer(self):
        r = raft_target_dp("unobtainium", "cdb", 4.0, 50)
        assert "error" in r

    def test_target_dp_invalid(self):
        r = raft_target_dp("styrene", "cdb", -4.0, 50)
        assert "error" in r
