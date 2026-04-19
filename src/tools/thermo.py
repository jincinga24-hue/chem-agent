"""Thermodynamic calculations for ChemE problems."""
import math


# Antoine coefficients: log10(P_kPa) = A - B / (C + T_C)
# Source: NIST webbook / Reid et al. "Properties of Gases and Liquids"
# Valid within stated temperature ranges approximately.
# A values converted to kPa form where originally in mmHg: A_kPa = A_mmHg - log10(7.5006) = A_mmHg - 0.87498.
ANTOINE_COEFFS = {
    "water":    {"A": 7.19621, "B": 1730.630, "C": 233.426, "range_c": (1, 100)},
    "ethanol":  {"A": 7.24677, "B": 1598.673, "C": 226.720, "range_c": (20, 93)},
    "methanol": {"A": 7.20519, "B": 1581.993, "C": 239.711, "range_c": (-16, 91)},
    "benzene":  {"A": 6.03067, "B": 1211.033, "C": 220.790, "range_c": (8, 103)},
    "toluene":  {"A": 6.07966, "B": 1344.800, "C": 219.482, "range_c": (6, 137)},
    "acetone":  {"A": 6.24216, "B": 1210.595, "C": 229.664, "range_c": (-13, 55)},
}

R_KPA_L_MOL_K = 8.314 / 1000 * 1000  # 8.314 J/(mol K) = 8.314 kPa·L/(mol·K)


def antoine_vapor_pressure(compound: str, temperature_c: float) -> dict:
    key = compound.strip().lower()
    if key not in ANTOINE_COEFFS:
        return {
            "error": f"No Antoine coefficients for '{compound}'. Known: {sorted(ANTOINE_COEFFS.keys())}"
        }
    c = ANTOINE_COEFFS[key]
    lo, hi = c["range_c"]
    in_range = lo <= temperature_c <= hi
    log_p = c["A"] - c["B"] / (c["C"] + temperature_c)
    p_kpa = 10 ** log_p
    return {
        "compound": key,
        "temperature_c": temperature_c,
        "vapor_pressure_kpa": round(p_kpa, 4),
        "in_valid_range": in_range,
        "valid_range_c": [lo, hi],
    }


def ideal_gas_volume(moles: float, temperature_k: float, pressure_kpa: float) -> dict:
    if pressure_kpa <= 0 or temperature_k <= 0 or moles <= 0:
        return {"error": "moles, temperature_k, pressure_kpa must all be positive"}
    v_l = moles * R_KPA_L_MOL_K * temperature_k / pressure_kpa
    return {
        "moles": moles,
        "temperature_k": temperature_k,
        "pressure_kpa": pressure_kpa,
        "volume_l": round(v_l, 4),
    }
