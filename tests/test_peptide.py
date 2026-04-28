"""Unit tests for peptide / AMP descriptor tool."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools.peptide import peptide_properties, helical_wheel_positions


class TestPeptideProperties:
    def test_basic_sequence(self):
        # Glycylglycine (GG): MW = 2*57.05 + 18.015 = 132.12 g/mol
        r = peptide_properties("GG")
        assert "error" not in r
        assert abs(r["mw_g_per_mol"] - 132.12) < 0.1
        assert r["length"] == 2

    def test_lowercase_accepted(self):
        r = peptide_properties("ggg")
        assert "error" not in r
        assert r["sequence"] == "GGG"

    def test_invalid_letter(self):
        r = peptide_properties("XOZ")
        assert "error" in r

    def test_empty_sequence(self):
        r = peptide_properties("")
        assert "error" in r

    def test_polylysine_is_strongly_cationic(self):
        # 10x Lys at pH 7.4 — each K contributes ~+1, plus N-term ~+1, minus C-term ~-1.
        # Expected: ~+10
        r = peptide_properties("KKKKKKKKKK", pH=7.4)
        assert r["net_charge_at_pH"] > 9.5

    def test_polyglutamate_is_strongly_anionic(self):
        # 10x Glu at pH 7.4 — each E contributes ~-1.
        r = peptide_properties("EEEEEEEEEE", pH=7.4)
        assert r["net_charge_at_pH"] < -9.0

    def test_polyalanine_neutral_at_ph7(self):
        # No ionizable side chains, just N+ and C- termini → ~0 at pH 7.
        r = peptide_properties("AAAAAA", pH=7.4)
        assert abs(r["net_charge_at_pH"]) < 0.5

    def test_polyleucine_high_hydrophobicity_low_moment(self):
        # All same residue → no asymmetry → near-zero moment.
        r = peptide_properties("LLLLLLLLLL")
        assert r["mean_hydrophobicity_kd"] > 3.0  # L is +3.8
        assert r["hydrophobic_moment_alpha"] < 0.5

    def test_amphipathic_helix_high_moment(self):
        # KKLLKLLKLLKLL: alternating K (charged) and LL (hydrophobic) — model amphipathic helix.
        # Should produce a notably higher μH than poly-leucine.
        amphipathic = peptide_properties("KKLLKLLKLLKLL")
        polyL = peptide_properties("LLLLLLLLLLLLL")  # same length
        assert amphipathic["hydrophobic_moment_alpha"] > polyL["hydrophobic_moment_alpha"]

    def test_amp_classification_for_amphipathic_cation(self):
        r = peptide_properties("KKLLKLLKLLKLL")
        assert r["net_charge_at_pH"] >= 3.0
        assert "AMP-like" in r["classification"]

    def test_melittin_is_amphipathic_and_cationic(self):
        # Melittin: GIGAVLKVLTTGLPALISWIKRKRQQ — classic AMP, +5 to +6 at pH 7.
        r = peptide_properties("GIGAVLKVLTTGLPALISWIKRKRQQ")
        assert 4.5 < r["net_charge_at_pH"] < 6.5
        assert r["hydrophobic_moment_alpha"] > 0.5
        assert "AMP-like" in r["classification"] or "Cationic" in r["classification"]

    def test_helix_propensity_glycine_low_alanine_high(self):
        gly = peptide_properties("GGGGG")
        ala = peptide_properties("AAAAA")
        # Chou-Fasman: G=0.57 (helix breaker), A=1.42 (strong former)
        assert gly["mean_helix_propensity"] < 0.7
        assert ala["mean_helix_propensity"] > 1.3


class TestHelicalWheel:
    def test_returns_one_position_per_residue(self):
        r = helical_wheel_positions("KKLLKLLKLLKLL")
        assert "error" not in r
        assert len(r["positions"]) == 13
        # First residue at angle 0.
        assert r["positions"][0]["angle_deg"] == 0.0
        # Second residue at 100°.
        assert abs(r["positions"][1]["angle_deg"] - 100.0) < 0.01

    def test_invalid_sequence(self):
        r = helical_wheel_positions("ZZZ")
        assert "error" in r
