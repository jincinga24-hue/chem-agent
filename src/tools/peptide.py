"""Peptide / antimicrobial peptide (AMP) descriptors for ChemAgent.

References
----------
- Kyte, J. & Doolittle, R.F. J. Mol. Biol. 157 (1982) 105–132.
  Hydropathy scale.
- Eisenberg, D. et al. Nature 299 (1982) 371–374.
  Hydrophobic moment as a measure of α-helix amphipathicity.
- Chou, P.Y. & Fasman, G.D. Biochemistry 13 (1974) 222–245.
  Secondary structure propensities.
- Lehninger, "Principles of Biochemistry" 7th ed., Table 3-1.
  Amino acid pKa values.
- Wimley, W.C. ACS Chem. Biol. 5 (2010) 905–917.
  AMP design heuristics: charge +3 to +9, μH > 0.4 favours antimicrobial activity.

Why this matters for SNAPPs / Qiao group
----------------------------------------
SNAPPs (Structurally Nanoengineered Antimicrobial Peptide Polymers) are star polymers
whose arms are short cationic / amphipathic peptide sequences. The two design knobs
are net charge (drives selectivity for negatively-charged bacterial membranes) and
hydrophobic moment (drives membrane disruption). This module computes both.
"""
import math


# Average residue masses (g/mol) — peptide-bond form, water already removed.
# Source: Unimod / standard biochemistry tables.
RESIDUE_MASS = {
    "A": 71.08,  "R": 156.19, "N": 114.10, "D": 115.09, "C": 103.14,
    "E": 129.12, "Q": 128.13, "G": 57.05,  "H": 137.14, "I": 113.16,
    "L": 113.16, "K": 128.17, "M": 131.20, "F": 147.18, "P": 97.12,
    "S": 87.08,  "T": 101.10, "W": 186.21, "Y": 163.18, "V": 99.13,
}
WATER_MASS = 18.015

# Kyte-Doolittle hydropathy index (positive = hydrophobic).
KD_HYDROPHOBICITY = {
    "A":  1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C":  2.5,
    "E": -3.5, "Q": -3.5, "G": -0.4, "H": -3.2, "I":  4.5,
    "L":  3.8, "K": -3.9, "M":  1.9, "F":  2.8, "P": -1.6,
    "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V":  4.2,
}

# Chou-Fasman α-helix propensity P_α (>1.0 favours helix).
HELIX_PROPENSITY = {
    "A": 1.42, "R": 0.98, "N": 0.67, "D": 1.01, "C": 0.70,
    "E": 1.51, "Q": 1.11, "G": 0.57, "H": 1.00, "I": 1.08,
    "L": 1.21, "K": 1.16, "M": 1.45, "F": 1.13, "P": 0.57,
    "S": 0.77, "T": 0.83, "W": 1.08, "Y": 0.69, "V": 1.06,
}

# pKa values for ionizable groups (Lehninger).
PKA_SIDE_CHAIN = {
    "C": 8.3, "D": 3.65, "E": 4.25, "H": 6.0,
    "K": 10.5, "R": 12.4, "Y": 10.07,
}
PKA_N_TERM = 9.0
PKA_C_TERM = 2.0
ACIDIC = {"C", "D", "E", "Y"}  # negative when deprotonated
BASIC = {"H", "K", "R"}        # positive when protonated


def _validate_sequence(seq: str) -> tuple[str, dict | None]:
    s = seq.strip().upper()
    if not s:
        return s, {"error": "Empty sequence"}
    bad = [c for c in s if c not in RESIDUE_MASS]
    if bad:
        return s, {"error": f"Unknown amino acid letters: {sorted(set(bad))}. Use single-letter codes for the standard 20."}
    return s, None


def _net_charge(seq: str, pH: float) -> float:
    """Henderson-Hasselbalch sum over all ionizable groups."""
    pos = 1.0 / (1.0 + 10 ** (pH - PKA_N_TERM))         # N-terminus
    neg = 1.0 / (1.0 + 10 ** (PKA_C_TERM - pH))         # C-terminus
    for aa in seq:
        if aa in BASIC:
            pos += 1.0 / (1.0 + 10 ** (pH - PKA_SIDE_CHAIN[aa]))
        elif aa in ACIDIC:
            neg += 1.0 / (1.0 + 10 ** (PKA_SIDE_CHAIN[aa] - pH))
    return pos - neg


def _hydrophobic_moment(seq: str, angle_deg: float = 100.0) -> float:
    """Eisenberg hydrophobic moment.

    μH = (1/N) sqrt[ (Σ H_i sin(δ·i))^2 + (Σ H_i cos(δ·i))^2 ]

    δ = 100° for α-helix (3.6 residues per turn). δ = 180° for β-strand.
    Returns absolute moment using Kyte-Doolittle scale.
    """
    delta = math.radians(angle_deg)
    sum_sin = 0.0
    sum_cos = 0.0
    for i, aa in enumerate(seq):
        h = KD_HYDROPHOBICITY[aa]
        sum_sin += h * math.sin(delta * i)
        sum_cos += h * math.cos(delta * i)
    return math.sqrt(sum_sin ** 2 + sum_cos ** 2) / len(seq)


def peptide_properties(sequence: str, pH: float = 7.4) -> dict:
    """Compute biophysical descriptors used in AMP design.

    Parameters
    ----------
    sequence : str   Single-letter amino acid sequence (e.g. "KKLLKLLKLLKLL").
                     Lowercase OK. Standard 20 amino acids only.
    pH : float       For net charge calculation (default physiological 7.4).

    Returns
    -------
    dict with:
      length, mw_g_per_mol, net_charge_at_pH, mean_hydrophobicity (KD),
      hydrophobic_moment_alpha (μH at δ=100°), hydrophobic_moment_beta (δ=180°),
      mean_helix_propensity, classification (heuristic AMP-likeness).
    """
    seq, err = _validate_sequence(sequence)
    if err:
        return err

    n = len(seq)
    mw = sum(RESIDUE_MASS[aa] for aa in seq) + WATER_MASS
    charge = _net_charge(seq, pH)
    mean_h = sum(KD_HYDROPHOBICITY[aa] for aa in seq) / n
    mu_h_alpha = _hydrophobic_moment(seq, 100.0)
    mu_h_beta = _hydrophobic_moment(seq, 180.0)
    mean_helix = sum(HELIX_PROPENSITY[aa] for aa in seq) / n

    # Wimley-style heuristic for AMP-likeness — coarse, descriptive only.
    amp_like = charge >= 3.0 and mu_h_alpha >= 0.4 and n >= 8
    if amp_like:
        classification = "AMP-like (cationic + amphipathic, n>=8)"
    elif charge >= 3.0:
        classification = "Cationic but low amphipathicity"
    elif mu_h_alpha >= 0.4:
        classification = "Amphipathic but not cationic"
    else:
        classification = "Neither strongly cationic nor amphipathic"

    return {
        "sequence": seq,
        "length": n,
        "mw_g_per_mol": round(mw, 2),
        "net_charge_at_pH": round(charge, 3),
        "pH": pH,
        "mean_hydrophobicity_kd": round(mean_h, 3),
        "hydrophobic_moment_alpha": round(mu_h_alpha, 4),
        "hydrophobic_moment_beta": round(mu_h_beta, 4),
        "mean_helix_propensity": round(mean_helix, 3),
        "classification": classification,
        "scale": "Kyte-Doolittle (1982)",
    }


def helical_wheel_positions(sequence: str) -> dict:
    """Project residues onto an α-helical wheel (100° per residue).

    Useful for visualizing amphipathicity — hydrophobic and polar residues
    cluster on opposite faces in amphipathic helices.
    """
    seq, err = _validate_sequence(sequence)
    if err:
        return err
    delta = math.radians(100.0)
    positions = []
    for i, aa in enumerate(seq):
        positions.append({
            "index": i + 1,
            "residue": aa,
            "angle_deg": round((i * 100.0) % 360.0, 2),
            "hydrophobicity_kd": KD_HYDROPHOBICITY[aa],
        })
    return {"sequence": seq, "positions": positions}
