"""Fluid mechanics tools for pipe-flow and pipe-network problems.

Every literature value (roughness, standard pipe ID, fitting K, fluid
properties) returns a `source` dict so the agent can cite a published
reference — lecture notes and generic webpages are not acceptable for
ENGR30002-style assignments.

References encoded here:
  - Crane Co. (2013). Technical Paper No. 410: Flow of Fluids Through
    Valves, Fittings, and Pipe. Crane Co., Stamford, CT. ISBN 1-40052-712-0.
  - Moody, L.F. (1944). "Friction Factors for Pipe Flow." Trans. ASME,
    66(8), 671-684.
  - Colebrook, C.F. (1939). "Turbulent flow in pipes, with particular
    reference to the transition region between the smooth and rough pipe
    laws." J. Inst. Civil Engineers, 11(4), 133-156.
  - Swamee, P.K. and Jain, A.K. (1976). "Explicit equations for pipe-flow
    problems." J. Hydraulics Div. ASCE, 102(HY5), 657-664.
  - Perry, R.H. and Green, D.W. (2008). Perry's Chemical Engineers'
    Handbook, 8th ed. McGraw-Hill. ISBN 978-0071422949.
  - IAPWS (2008). Release on the IAPWS Formulation 2008 for the
    Viscosity of Ordinary Water Substance.
  - ASME B36.10M-2018. Welded and Seamless Wrought Steel Pipe.
  - AS 1579-2001. Arc-welded steel pipes and fittings for water and waste.
  - AS/NZS 4792:2006. Hot-dip galvanized (zinc) coatings on ferrous hollow
    sections.
  - AS/NZS 4130:2018. Polyethylene (PE) pipes for pressure applications.
"""
import math
from typing import Optional


# --- Reference registry ---------------------------------------------------
# A single source of truth for citations so the agent can report exactly
# which reference was used for any literature value.
REFERENCES = {
    "crane_tp410": {
        "citation": "Crane Co. (2013). Technical Paper No. 410: Flow of Fluids Through Valves, Fittings, and Pipe. Stamford, CT.",
        "type": "technical_paper",
        "isbn": "1-40052-712-0",
    },
    "moody_1944": {
        "citation": "Moody, L.F. (1944). Friction Factors for Pipe Flow. Trans. ASME, 66(8), 671-684.",
        "type": "journal_article",
        "doi": "10.1115/1.4018140",
    },
    "colebrook_1939": {
        "citation": "Colebrook, C.F. (1939). Turbulent flow in pipes. J. Inst. Civil Engineers, 11(4), 133-156.",
        "type": "journal_article",
        "doi": "10.1680/ijoti.1939.13150",
    },
    "swamee_jain_1976": {
        "citation": "Swamee, P.K. & Jain, A.K. (1976). Explicit equations for pipe-flow problems. J. Hydraulics Div. ASCE, 102(HY5), 657-664.",
        "type": "journal_article",
    },
    "perry_8ed": {
        "citation": "Perry, R.H. & Green, D.W. (2008). Perry's Chemical Engineers' Handbook, 8th ed. McGraw-Hill.",
        "type": "handbook",
        "isbn": "978-0071422949",
    },
    "iapws_2008_visc": {
        "citation": "IAPWS (2008). Release on the IAPWS Formulation 2008 for the Viscosity of Ordinary Water Substance.",
        "type": "standard",
    },
    "asme_b36_10m": {
        "citation": "ASME B36.10M-2018. Welded and Seamless Wrought Steel Pipe.",
        "type": "standard",
    },
    "as_1579": {
        "citation": "AS 1579-2001. Arc-welded steel pipes and fittings for water and waste. Standards Australia.",
        "type": "standard",
    },
    "as_nzs_4130": {
        "citation": "AS/NZS 4130:2018. Polyethylene (PE) pipes for pressure applications.",
        "type": "standard",
    },
}

G = 9.81  # m/s^2


# --- Fluid properties -----------------------------------------------------

def water_properties(temperature_c: float) -> dict:
    """Density (kg/m^3) and dynamic viscosity (Pa·s) for liquid water at 1 atm.

    Uses simple polynomial fits accurate to <0.5% over 0-100 C. For higher
    accuracy use IAPWS-IF97 tables directly.

    Source: Perry's Chemical Engineers' Handbook 8th ed., Table 2-32 (density)
            and IAPWS 2008 (viscosity).
    """
    T = temperature_c
    if T < 0 or T > 100:
        return {"error": f"temperature {T} C outside 0-100 C range"}

    # Kell (1975) formulation for liquid water density at 1 atm, kg/m^3.
    # Fits Perry's Table 2-32 to <0.01 kg/m^3 over 0-100 C.
    rho = (
        999.83952
        + 16.945176 * T
        - 7.9870401e-3 * T**2
        - 46.170461e-6 * T**3
        + 105.56302e-9 * T**4
        - 280.54253e-12 * T**5
    ) / (1 + 16.87985e-3 * T)

    # Vogel equation for water viscosity (Pa·s). Coefficients fit IAPWS data
    # over 0-100 C to ~1%. Returned in Pa·s.
    T_k = T + 273.15
    mu = math.exp(-3.7188 + 578.919 / (T_k - 137.546)) * 1e-3

    return {
        "temperature_c": T,
        "density_kg_m3": round(rho, 3),
        "viscosity_pa_s": round(mu, 8),
        "kinematic_viscosity_m2_s": round(mu / rho, 10),
        "source": {
            "density": REFERENCES["perry_8ed"],
            "viscosity": REFERENCES["iapws_2008_visc"],
        },
    }


# --- Pipe roughness -------------------------------------------------------

# Equivalent sand-grain roughness in mm.
# Values from Moody (1944) and Crane TP-410 Appendix A-23.
ROUGHNESS_MM = {
    "drawn_tubing":     {"eps_mm": 0.0015, "source": "crane_tp410"},
    "commercial_steel": {"eps_mm": 0.046,  "source": "moody_1944"},
    "wrought_iron":     {"eps_mm": 0.046,  "source": "moody_1944"},
    "galvanized_iron":  {"eps_mm": 0.15,   "source": "moody_1944"},
    "cast_iron":        {"eps_mm": 0.26,   "source": "moody_1944"},
    "concrete":         {"eps_mm": 1.5,    "source": "crane_tp410"},  # mid of 0.3-3.0
    "riveted_steel":    {"eps_mm": 3.0,    "source": "moody_1944"},
    "pvc":              {"eps_mm": 0.0015, "source": "crane_tp410"},
    "hdpe":             {"eps_mm": 0.007,  "source": "as_nzs_4130"},
    "copper":           {"eps_mm": 0.0015, "source": "crane_tp410"},
    "stainless_steel":  {"eps_mm": 0.015,  "source": "perry_8ed"},
}


def pipe_roughness(material: str) -> dict:
    """Equivalent sand-grain roughness (mm) for common pipe materials."""
    key = material.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in ROUGHNESS_MM:
        return {
            "error": f"unknown material '{material}'. Known: {sorted(ROUGHNESS_MM.keys())}"
        }
    entry = ROUGHNESS_MM[key]
    return {
        "material": key,
        "roughness_mm": entry["eps_mm"],
        "roughness_m": entry["eps_mm"] * 1e-3,
        "source": REFERENCES[entry["source"]],
    }


# --- Standard pipe inside diameters ---------------------------------------

# Nominal size (DN, mm) → inside diameter (mm) for selected standards.
# Schedule 40 steel per ASME B36.10M-2018, Table 1.
STD_STEEL_SCH40 = {
    15:  {"od_mm": 21.3,  "wall_mm": 2.77, "id_mm": 15.80},
    20:  {"od_mm": 26.7,  "wall_mm": 2.87, "id_mm": 20.93},
    25:  {"od_mm": 33.4,  "wall_mm": 3.38, "id_mm": 26.64},
    32:  {"od_mm": 42.2,  "wall_mm": 3.56, "id_mm": 35.05},
    40:  {"od_mm": 48.3,  "wall_mm": 3.68, "id_mm": 40.89},
    50:  {"od_mm": 60.3,  "wall_mm": 3.91, "id_mm": 52.50},
    65:  {"od_mm": 73.0,  "wall_mm": 5.16, "id_mm": 62.68},
    80:  {"od_mm": 88.9,  "wall_mm": 5.49, "id_mm": 77.93},
    100: {"od_mm": 114.3, "wall_mm": 6.02, "id_mm": 102.26},
    150: {"od_mm": 168.3, "wall_mm": 7.11, "id_mm": 154.05},
    200: {"od_mm": 219.1, "wall_mm": 8.18, "id_mm": 202.72},
}

# HDPE PN16 SDR11 per AS/NZS 4130:2018.
STD_HDPE_PN16 = {
    25:  {"od_mm": 25,  "wall_mm": 2.3, "id_mm": 20.4},
    32:  {"od_mm": 32,  "wall_mm": 3.0, "id_mm": 26.0},
    40:  {"od_mm": 40,  "wall_mm": 3.7, "id_mm": 32.6},
    50:  {"od_mm": 50,  "wall_mm": 4.6, "id_mm": 40.8},
    63:  {"od_mm": 63,  "wall_mm": 5.8, "id_mm": 51.4},
    75:  {"od_mm": 75,  "wall_mm": 6.8, "id_mm": 61.4},
    90:  {"od_mm": 90,  "wall_mm": 8.2, "id_mm": 73.6},
    110: {"od_mm": 110, "wall_mm": 10.0, "id_mm": 90.0},
    160: {"od_mm": 160, "wall_mm": 14.6, "id_mm": 130.8},
    200: {"od_mm": 200, "wall_mm": 18.2, "id_mm": 163.6},
}

PIPE_STANDARDS = {
    "steel_sch40":   {"table": STD_STEEL_SCH40, "source": "asme_b36_10m"},
    "hdpe_pn16":     {"table": STD_HDPE_PN16,   "source": "as_nzs_4130"},
}


def standard_pipe_id(standard: str, nominal_size_mm: float) -> dict:
    """Look up the inside diameter for a standard nominal pipe size.

    standard: one of 'steel_sch40', 'hdpe_pn16'.
    nominal_size_mm: DN in mm.
    """
    key = standard.strip().lower()
    if key not in PIPE_STANDARDS:
        return {"error": f"unknown standard '{standard}'. Known: {sorted(PIPE_STANDARDS.keys())}"}
    table = PIPE_STANDARDS[key]["table"]
    if nominal_size_mm not in table:
        return {
            "error": f"no DN{int(nominal_size_mm)} in {key}. Available: {sorted(table.keys())}"
        }
    row = table[nominal_size_mm]
    return {
        "standard": key,
        "nominal_size_mm": nominal_size_mm,
        "outside_diameter_mm": row["od_mm"],
        "wall_thickness_mm": row["wall_mm"],
        "inside_diameter_mm": row["id_mm"],
        "inside_diameter_m": row["id_mm"] * 1e-3,
        "source": REFERENCES[PIPE_STANDARDS[key]["source"]],
    }


# --- Fittings -------------------------------------------------------------

# Resistance coefficient K for fully turbulent flow.
# Source: Crane TP-410 Appendix A-26 (fittings) and A-27 (valves).
FITTING_K = {
    "elbow_90_standard":   0.75,
    "elbow_90_long_radius": 0.45,
    "elbow_45_standard":   0.35,
    "tee_through_run":     0.40,
    "tee_branch_flow":     1.00,
    "gate_valve_open":     0.15,
    "globe_valve_open":    10.0,
    "ball_valve_open":     0.05,
    "check_valve_swing":   2.5,
    "entrance_sharp":      0.50,
    "exit_to_tank":        1.00,
}


def fitting_k(fitting: str) -> dict:
    key = fitting.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in FITTING_K:
        return {"error": f"unknown fitting '{fitting}'. Known: {sorted(FITTING_K.keys())}"}
    return {
        "fitting": key,
        "K": FITTING_K[key],
        "source": REFERENCES["crane_tp410"],
    }


# --- Reynolds number and friction factor ---------------------------------

def reynolds_number(density_kg_m3: float, velocity_m_s: float,
                    diameter_m: float, viscosity_pa_s: float) -> dict:
    if viscosity_pa_s <= 0 or diameter_m <= 0:
        return {"error": "viscosity and diameter must be positive"}
    Re = density_kg_m3 * abs(velocity_m_s) * diameter_m / viscosity_pa_s
    if Re < 2300:
        regime = "laminar"
    elif Re < 4000:
        regime = "transitional"
    else:
        regime = "turbulent"
    return {"reynolds_number": round(Re, 1), "regime": regime}


def friction_factor_colebrook(reynolds: float, roughness_m: float,
                              diameter_m: float) -> dict:
    """Darcy friction factor by iterative solution of the Colebrook-White
    equation:  1/sqrt(f) = -2 log10(eps/(3.7D) + 2.51/(Re·sqrt(f)))

    For Re < 2300 returns laminar f = 64/Re. For 2300 <= Re < 4000 the
    transitional regime is flagged but Colebrook is still evaluated.
    """
    if reynolds <= 0 or diameter_m <= 0 or roughness_m < 0:
        return {"error": "reynolds, diameter must be positive; roughness non-negative"}

    if reynolds < 2300:
        return {
            "friction_factor": 64.0 / reynolds,
            "regime": "laminar",
            "method": "f = 64/Re",
            "source": REFERENCES["moody_1944"],
        }

    eps_over_d = roughness_m / diameter_m

    # Initial guess from Swamee-Jain
    f = 0.25 / (math.log10(eps_over_d / 3.7 + 5.74 / reynolds**0.9)) ** 2

    for _ in range(50):
        rhs = -2.0 * math.log10(eps_over_d / 3.7 + 2.51 / (reynolds * math.sqrt(f)))
        f_new = 1.0 / rhs**2
        if abs(f_new - f) < 1e-10:
            f = f_new
            break
        f = f_new

    return {
        "friction_factor": round(f, 6),
        "reynolds": reynolds,
        "roughness_m": roughness_m,
        "diameter_m": diameter_m,
        "eps_over_d": round(eps_over_d, 7),
        "regime": "turbulent" if reynolds >= 4000 else "transitional",
        "method": "Colebrook-White (iterative)",
        "source": REFERENCES["colebrook_1939"],
    }


def friction_factor_swamee_jain(reynolds: float, roughness_m: float,
                                diameter_m: float) -> dict:
    """Explicit Swamee-Jain approximation to Colebrook (turbulent only).
    Accurate to ~1% for 5e3 <= Re <= 1e8 and 1e-6 <= eps/D <= 1e-2.
    """
    if reynolds < 2300:
        return {
            "friction_factor": 64.0 / reynolds,
            "regime": "laminar",
            "method": "f = 64/Re",
        }
    eps_over_d = roughness_m / diameter_m
    f = 0.25 / (math.log10(eps_over_d / 3.7 + 5.74 / reynolds**0.9)) ** 2
    return {
        "friction_factor": round(f, 6),
        "eps_over_d": round(eps_over_d, 7),
        "method": "Swamee-Jain (explicit)",
        "source": REFERENCES["swamee_jain_1976"],
    }


# --- Three-reservoir pipe network solver ---------------------------------

def solve_three_reservoir_network(pipes: list, fluid: dict,
                                  max_iter: int = 100,
                                  tol: float = 1e-6) -> dict:
    """Solve the classic 3-reservoir problem: three tanks joined at a common
    junction J via three pipes.

    Each entry in `pipes` is a dict with:
      - P_pa:         absolute pressure at tank surface (Pa)
      - z_surface_m:  elevation of free surface (z_i + h_i) (m)
      - z_pipe_m:     elevation of pipe entrance at the tank (m)  [unused for
                      energy balance; kept for reference]
      - length_m:     pipe length (m)
      - diameter_m:   pipe inside diameter (m)
      - roughness_m:  equivalent sand-grain roughness (m)
      - sum_K:        sum of resistance coefficients for fittings + entrance
                      + exit (dimensionless)

    `fluid` has: density_kg_m3, viscosity_pa_s.

    `z_J_m` is the junction elevation.  Pass it separately.

    Returns flows Q_i (m^3/s, positive = tank i → J), velocities, friction
    factors, and junction pressure P_J (Pa).  Continuity is Q1+Q2+Q3 = 0.

    Requires scipy. Uses fsolve on 4 unknowns (Q1, Q2, Q3, P_J) and 4
    equations (3 extended-Bernoulli + continuity).
    """
    try:
        from scipy.optimize import fsolve
    except ImportError:
        return {"error": "scipy is required for the network solver"}

    if len(pipes) != 3:
        return {"error": "exactly 3 pipes are required"}
    for i, p in enumerate(pipes):
        required = {"P_pa", "z_surface_m", "length_m", "diameter_m",
                    "roughness_m", "sum_K"}
        missing = required - set(p.keys())
        if missing:
            return {"error": f"pipe {i}: missing keys {sorted(missing)}"}

    z_J = fluid.get("z_J_m")
    if z_J is None:
        return {"error": "fluid must contain z_J_m (junction elevation)"}
    rho = fluid["density_kg_m3"]
    mu = fluid["viscosity_pa_s"]

    areas = [math.pi * p["diameter_m"] ** 2 / 4.0 for p in pipes]

    def head_loss_signed(Q, pipe, area):
        """Signed head loss in the direction of flow (m). Loss is positive
        in the direction of flow; returned with sign so the energy equation
        becomes H_i - H_J - loss_signed = 0 regardless of flow direction."""
        if Q == 0:
            return 0.0
        v = Q / area
        Re = rho * abs(v) * pipe["diameter_m"] / mu
        if Re < 2300:
            f = 64.0 / Re
        else:
            eps_over_d = pipe["roughness_m"] / pipe["diameter_m"]
            ff = 0.25 / (math.log10(eps_over_d / 3.7 + 5.74 / Re**0.9)) ** 2
            for _ in range(30):
                rhs = -2.0 * math.log10(eps_over_d / 3.7 + 2.51 / (Re * math.sqrt(ff)))
                ff_new = 1.0 / rhs**2
                if abs(ff_new - ff) < 1e-10:
                    ff = ff_new
                    break
                ff = ff_new
            f = ff
        # Total head loss magnitude: friction + fittings + exit/entrance bundled in sum_K
        # Velocity head at J counted via sum_K including exit loss or kinetic term.
        loss_mag = (f * pipe["length_m"] / pipe["diameter_m"] + pipe["sum_K"]) * v**2 / (2 * G)
        return math.copysign(loss_mag, Q)

    def residuals(x):
        Q1, Q2, Q3, P_J = x
        Qs = [Q1, Q2, Q3]
        eqs = []
        for Q, pipe, area in zip(Qs, pipes, areas):
            H_i = pipe["P_pa"] / (rho * G) + pipe["z_surface_m"]
            H_J = P_J / (rho * G) + z_J
            eqs.append(H_i - H_J - head_loss_signed(Q, pipe, area))
        eqs.append(Q1 + Q2 + Q3)
        return eqs

    # Initial guess: crude — assume highest-head tank feeds the others.
    heads = [p["P_pa"] / (rho * G) + p["z_surface_m"] for p in pipes]
    max_idx = heads.index(max(heads))
    Q0 = [0.001] * 3
    Q0[max_idx] = 0.01
    total = sum(Q0)
    Q0[(max_idx + 1) % 3] -= total / 2
    Q0[(max_idx + 2) % 3] -= total / 2
    P_J0 = sum(p["P_pa"] for p in pipes) / 3.0

    try:
        sol, info, ier, msg = fsolve(residuals, Q0 + [P_J0],
                                     full_output=True, xtol=tol, maxfev=max_iter * 10)
    except Exception as e:
        return {"error": f"solver failed: {type(e).__name__}: {e}"}

    if ier != 1:
        return {"error": f"solver did not converge: {msg}", "last_iterate": list(sol)}

    Q1, Q2, Q3, P_J = sol
    Qs = [Q1, Q2, Q3]
    result = {
        "junction_pressure_pa": round(float(P_J), 2),
        "junction_pressure_kpa": round(float(P_J) / 1000.0, 3),
        "continuity_residual_m3_s": round(float(Q1 + Q2 + Q3), 10),
        "pipes": [],
    }
    for i, (Q, pipe, area) in enumerate(zip(Qs, pipes, areas)):
        v = Q / area
        Re = rho * abs(v) * pipe["diameter_m"] / mu
        direction = "tank_to_junction" if Q > 0 else "junction_to_tank"
        result["pipes"].append({
            "pipe_index": i + 1,
            "flow_m3_s": round(float(Q), 8),
            "flow_L_s": round(float(Q) * 1000.0, 5),
            "velocity_m_s": round(float(v), 5),
            "reynolds": round(float(Re), 1),
            "direction": direction,
        })
    return result
