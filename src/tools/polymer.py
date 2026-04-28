"""RAFT polymerization kinetics for ChemAgent.

References
----------
- Moad, Rizzardo, Thang. "Living radical polymerization by the RAFT process —
  a third update." Aust. J. Chem. 65 (2012) 985–1076.
- Odian, "Principles of Polymerization" 4th ed., Ch. 3 & 9.
- Müller, A. H. E. et al. Macromolecules 28 (1995) 4326. (dispersity in living systems)

Model (simplified, textbook level)
----------------------------------
Pseudo-steady-state radical concentration:
    [P•]_ss = sqrt(2 f kd [I] / kt)

First-order monomer consumption:
    x(t) = 1 - exp(-kp [P•]_ss t)

Ideal RAFT (assume all CTA consumed, no termination loss):
    DP_n(t) = x(t) [M]_0 / [CTA]_0
    Mn(t)  = DP_n(t) M_monomer + M_CTA

Dispersity (Müller form, simplified):
    Đ(t) = 1 + 1/DP_n(t) + (1/C_tr) (2 - x(t)) / x(t)

These approximations are acceptable for low-conversion (<70%), well-controlled
RAFT polymerizations. They break down at high conversion where termination
becomes significant.
"""
import math


R_J_MOL_K = 8.314


# Arrhenius parameters for monomer propagation: kp = A * exp(-Ea / R T)  [L/mol/s, J/mol]
# Sources: Beuermann & Buback IUPAC benchmarks (Prog. Polym. Sci. 27 (2002) 191).
MONOMER_DATA = {
    "styrene":    {"A_kp": 4.27e7, "Ea_kp": 32.5e3, "MW": 104.15},
    "mma":        {"A_kp": 2.67e6, "Ea_kp": 22.4e3, "MW": 100.12},
    "ma":         {"A_kp": 1.66e7, "Ea_kp": 17.7e3, "MW": 86.09},   # methyl acrylate
    "ba":         {"A_kp": 2.21e7, "Ea_kp": 17.9e3, "MW": 128.17},  # n-butyl acrylate
    "acrylamide": {"A_kp": 1.50e7, "Ea_kp": 18.0e3, "MW": 71.08},
    "vinyl_acetate": {"A_kp": 1.47e7, "Ea_kp": 20.4e3, "MW": 86.09},
}

# Initiator decomposition: kd = A exp(-Ea / RT)  [1/s], f = initiator efficiency
# Sources: Brandrup, Polymer Handbook 4th ed., Sec. II.
INITIATOR_DATA = {
    "aibn": {"A_kd": 1.58e15, "Ea_kd": 130.0e3, "f": 0.6},
    "bpo":  {"A_kd": 7.11e13, "Ea_kd": 121.3e3, "f": 0.5},
    "v-65": {"A_kd": 2.60e15, "Ea_kd": 120.4e3, "f": 0.7},
}

# RAFT chain transfer constants C_tr = k_tr / kp at 60-70 C, monomer-specific
# Source: Moad et al. (2012); values are representative, vary with monomer.
CTA_DATA = {
    "cdb":    {"C_tr": 6000.0, "MW": 272.39, "best_for": ["styrene", "mma"]},      # cumyl dithiobenzoate
    "ddmat":  {"C_tr":   30.0, "MW": 364.62, "best_for": ["ma", "ba", "acrylamide"]},  # 2-(dodecylthiocarbonothioylthio)-2-methylpropionic acid
    "cpadb":  {"C_tr":   30.0, "MW": 279.38, "best_for": ["ma", "ba", "acrylamide"]},  # 4-cyano-4-(phenylcarbonothioylthio)pentanoic acid
    "ctp":    {"C_tr":  150.0, "MW": 280.39, "best_for": ["ma", "ba"]},            # 4-cyano-4-(thiobenzoylthio)pentanoic acid
}

# Termination rate constant: ~1e8 L/mol/s for most monomers, weakly T-dependent.
# Coarse approximation; for high accuracy use chain-length-dependent kt.
KT_DEFAULT = 1.0e8


def _arrhenius(A: float, Ea_J_mol: float, T_K: float) -> float:
    return A * math.exp(-Ea_J_mol / (R_J_MOL_K * T_K))


def raft_kinetics(
    monomer: str,
    initiator: str,
    cta: str,
    M0: float,
    I0: float,
    CTA0: float,
    T_C: float,
    t_final_s: float,
    n_points: int = 50,
) -> dict:
    """Predict conversion, Mn, and dispersity over time for a RAFT polymerization.

    Parameters
    ----------
    monomer : str        e.g. "styrene", "mma", "ma", "ba", "acrylamide"
    initiator : str      e.g. "aibn", "bpo", "v-65"
    cta : str            RAFT agent, e.g. "cdb", "ddmat", "cpadb", "ctp"
    M0 : float           initial monomer concentration [mol/L]
    I0 : float           initial initiator concentration [mol/L]
    CTA0 : float         initial RAFT agent concentration [mol/L]
    T_C : float          temperature [Celsius]
    t_final_s : float    end time [seconds]
    n_points : int       number of samples (default 50)

    Returns
    -------
    dict with time series for conversion, Mn, dispersity, DP_n,
    plus the rate constants used and final values.
    """
    mon = monomer.strip().lower()
    ini = initiator.strip().lower()
    ct = cta.strip().lower()

    if mon not in MONOMER_DATA:
        return {"error": f"Unknown monomer '{monomer}'. Known: {sorted(MONOMER_DATA.keys())}"}
    if ini not in INITIATOR_DATA:
        return {"error": f"Unknown initiator '{initiator}'. Known: {sorted(INITIATOR_DATA.keys())}"}
    if ct not in CTA_DATA:
        return {"error": f"Unknown CTA '{cta}'. Known: {sorted(CTA_DATA.keys())}"}
    if M0 <= 0 or I0 <= 0 or CTA0 <= 0:
        return {"error": "M0, I0, CTA0 must all be positive"}
    if t_final_s <= 0 or n_points < 2:
        return {"error": "t_final_s must be > 0 and n_points >= 2"}

    T_K = T_C + 273.15
    m = MONOMER_DATA[mon]
    i = INITIATOR_DATA[ini]
    c = CTA_DATA[ct]

    kp = _arrhenius(m["A_kp"], m["Ea_kp"], T_K)
    kd = _arrhenius(i["A_kd"], i["Ea_kd"], T_K)
    kt = KT_DEFAULT
    f = i["f"]
    C_tr = c["C_tr"]

    # Pseudo-steady-state radical concentration (constant if [I] approx constant)
    P_dot_ss = math.sqrt(2.0 * f * kd * I0 / kt)

    # Time grid (skip t=0 to avoid divide-by-zero in dispersity formula; report t=0 separately)
    times = [t_final_s * k / (n_points - 1) for k in range(n_points)]

    series = {
        "time_s": [],
        "conversion": [],
        "DP_n": [],
        "Mn_g_per_mol": [],
        "dispersity": [],
    }
    for t in times:
        x = 1.0 - math.exp(-kp * P_dot_ss * t)
        if t == 0.0 or x < 1e-9:
            DP_n = 0.0
            Mn = c["MW"]
            disp = float("nan")
        else:
            DP_n = x * M0 / CTA0
            Mn = DP_n * m["MW"] + c["MW"]
            disp = 1.0 + (1.0 / DP_n if DP_n > 0 else 0.0) + (1.0 / C_tr) * (2.0 - x) / x
        series["time_s"].append(round(t, 3))
        series["conversion"].append(round(x, 5))
        series["DP_n"].append(round(DP_n, 3))
        series["Mn_g_per_mol"].append(round(Mn, 2))
        series["dispersity"].append(round(disp, 4) if not math.isnan(disp) else None)

    return {
        "inputs": {
            "monomer": mon,
            "initiator": ini,
            "cta": ct,
            "M0_mol_L": M0,
            "I0_mol_L": I0,
            "CTA0_mol_L": CTA0,
            "T_C": T_C,
            "t_final_s": t_final_s,
        },
        "rate_constants": {
            "kp_L_mol_s": kp,
            "kd_1_s": kd,
            "kt_L_mol_s": kt,
            "f": f,
            "C_tr": C_tr,
            "P_radical_ss_mol_L": P_dot_ss,
        },
        "final": {
            "conversion": series["conversion"][-1],
            "DP_n": series["DP_n"][-1],
            "Mn_g_per_mol": series["Mn_g_per_mol"][-1],
            "dispersity": series["dispersity"][-1],
        },
        "series": series,
        "model": "Pseudo-steady-state radicals + 1st-order monomer consumption + Müller dispersity. Valid for x<0.7.",
    }


def raft_target_dp(
    monomer: str,
    cta: str,
    M0: float,
    target_DP: float,
) -> dict:
    """Compute the [CTA]_0 needed to hit a target DP at full conversion.

    Useful inverse design: 'I want a 100-mer of styrene from M0=4 mol/L — how
    much CTA do I need?'  Answer: CTA0 = M0 / target_DP (assuming x = 1).
    """
    mon = monomer.strip().lower()
    ct = cta.strip().lower()
    if mon not in MONOMER_DATA:
        return {"error": f"Unknown monomer '{monomer}'"}
    if ct not in CTA_DATA:
        return {"error": f"Unknown CTA '{cta}'"}
    if M0 <= 0 or target_DP <= 0:
        return {"error": "M0 and target_DP must be positive"}

    CTA0 = M0 / target_DP
    target_Mn = target_DP * MONOMER_DATA[mon]["MW"] + CTA_DATA[ct]["MW"]
    return {
        "monomer": mon,
        "cta": ct,
        "M0_mol_L": M0,
        "target_DP": target_DP,
        "required_CTA0_mol_L": round(CTA0, 6),
        "target_Mn_g_per_mol": round(target_Mn, 2),
        "assumption": "Full conversion (x=1), ideal RAFT.",
    }
