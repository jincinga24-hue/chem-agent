"""Independent cross-validation: run the ENGR30002 Q2 three-reservoir
network through EPANET 2.2 (via epyt) and compare against our in-house
fsolve solver.

EPANET convention: tees/junctions are piezometric nodes (no exit loss,
velocity head is neglected). So the fair comparison is to drop the
K=1.0 exit-into-reservoir term we had originally bundled into sum_K.
The pipe loss equation becomes:

  h_loss = [ f * L/D + (sum of fittings + entrance) ] * v^2 / (2g)

Pressurised tanks are represented in EPANET as equivalent open
reservoirs with gauge head H_i = (P_i - P_atm)/(rho*g) + z_i + h_i.

Writes a plain-text .inp file, runs it, reports flows and P_J, and
compares to our Python solver run with the same minor-loss setup.
"""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.tools.fluids import (
    water_properties,
    solve_three_reservoir_network,
)

G = 9.81
P_ATM_PA = 101_325.0


# ---- Network definition (single source of truth) -----------------------
WATER_T_C = 20.0
Z_J = 2.0  # junction elevation (m)

# Each tank: absolute pressure (Pa) above free surface, surface elevation
# (z_i + h_i, m).
TANKS = [
    {"P_pa_abs": 500_000.0, "z_surface_m": 60.0, "label": "T1"},
    {"P_pa_abs": 200_000.0, "z_surface_m": 25.0, "label": "T2"},
    {"P_pa_abs": 101_325.0, "z_surface_m":  7.0, "label": "T3"},
]

# Pipes, tank-i to junction. sum_K here is fittings+entrance only
# (no K=1.0 exit, since J is a tee — see docstring).
# Aligned with the current submission (build.py / q2_network.m):
#   - Elbows and gate valve modelled via equivalent length (L_eq). Added to
#     the EPANET pipe length field as "effective length".
#   - Ball valve, globe valve, entrance K modelled via resistance coefficient
#     (kept as EPANET's minor-loss K per pipe).
#   - Tee at J: Pipe 1 = main run (no tee L_eq); Pipes 2 & 3 = branches with
#     L_eq = 90D each (also added to effective length).
PIPES = [
    {
        "label": "P1", "material": "commercial_steel",
        # L_eff = 100 + (2*30D + 7D) = 100 + 6.852 = 106.852 m
        "length_m": 100.0 + (2*30 + 7) * 0.10226,
        "diameter_m": 0.10226, "roughness_mm": 0.046,
        "sum_K_no_exit": 0.5,                     # entrance only (elbows/gate via L_eq)
    },
    {
        "label": "P2", "material": "hdpe",
        # L_eff = 150 + (15D elbow + 90D tee branch) = 157.728 m
        "length_m": 150.0 + (15 + 90) * 0.07360,
        "diameter_m": 0.07360, "roughness_mm": 0.0015,
        "sum_K_no_exit": 0.5 + 0.05,              # entrance + ball valve
    },
    {
        "label": "P3", "material": "galvanized_iron",
        # L_eff = 80 + (30D elbow + 90D tee branch) = 86.3 m
        "length_m":  80.0 + (30 + 90) * 0.05250,
        "diameter_m": 0.05250, "roughness_mm": 0.150,
        "sum_K_no_exit": 0.5 + 10.0,              # entrance + globe valve
    },
]


def build_inp() -> str:
    """Emit an EPANET 2.2 input file in SI units."""
    rho = water_properties(WATER_T_C)["density_kg_m3"]
    # Gauge head at each pressurised free surface, in metres of water.
    heads_gauge = [
        (t["P_pa_abs"] - P_ATM_PA) / (rho * G) + t["z_surface_m"]
        for t in TANKS
    ]

    mu = water_properties(WATER_T_C)["viscosity_pa_s"]
    nu_rel = (mu / rho) / 1.0e-6  # EPANET VISCOSITY is relative to 1e-6 m^2/s

    inp = []
    inp.append("[TITLE]")
    inp.append("ENGR30002 Q2 cross-validation — three-reservoir network")

    inp.append("[JUNCTIONS]")
    inp.append(";ID  Elev(m)  Demand  Pattern")
    inp.append(f" J    {Z_J}   0")

    inp.append("[RESERVOIRS]")
    inp.append(";ID  Head(m)  Pattern")
    for t, h in zip(TANKS, heads_gauge):
        inp.append(f" {t['label']}  {h:.6f}")

    inp.append("[TANKS]")

    inp.append("[PIPES]")
    inp.append(";ID From   To  Len(m) Dia(mm) Rough(mm) MinorLossK  Status")
    for t, p in zip(TANKS, PIPES):
        inp.append(
            f" {p['label']:3s} {t['label']:3s} J  "
            f"{p['length_m']:.3f}  {p['diameter_m']*1000:.3f}  "
            f"{p['roughness_mm']:.4f}  {p['sum_K_no_exit']:.4f}  Open"
        )

    inp.append("[PUMPS]")
    inp.append("[VALVES]")
    inp.append("[TAGS]")
    inp.append("[DEMANDS]")
    inp.append("[STATUS]")
    inp.append("[PATTERNS]")
    inp.append("[CURVES]")
    inp.append("[CONTROLS]")
    inp.append("[RULES]")
    inp.append("[ENERGY]")
    inp.append("[EMITTERS]")
    inp.append("[QUALITY]")
    inp.append("[SOURCES]")
    inp.append("[REACTIONS]")
    inp.append("[MIXING]")

    inp.append("[TIMES]")
    inp.append(" DURATION 0")
    inp.append(" HYDRAULIC TIMESTEP 1:00")
    inp.append(" QUALITY TIMESTEP 1:00")
    inp.append(" PATTERN TIMESTEP 1:00")
    inp.append(" REPORT TIMESTEP 1:00")
    inp.append(" REPORT START 0:00")

    inp.append("[REPORT]")
    inp.append(" STATUS YES")
    inp.append(" SUMMARY NO")
    inp.append(" PAGE 0")

    inp.append("[OPTIONS]")
    inp.append(" UNITS LPS")
    inp.append(" HEADLOSS D-W")
    inp.append(" SPECIFIC GRAVITY 1.0")
    inp.append(f" VISCOSITY {nu_rel:.6f}")
    inp.append(" TRIALS 100")
    inp.append(" ACCURACY 0.0000001")
    inp.append(" UNBALANCED STOP 10")
    inp.append(" PATTERN 1")
    inp.append(" DEMAND MULTIPLIER 1.0")
    inp.append(" EMITTER EXPONENT 0.5")
    inp.append(" QUALITY NONE")

    inp.append("[COORDINATES]")
    inp.append("[VERTICES]")
    inp.append("[LABELS]")
    inp.append("[BACKDROP]")

    inp.append("[END]")
    return "\n".join(inp)


def run_epanet(inp_text: str) -> dict:
    from epyt import epanet
    with tempfile.TemporaryDirectory() as td:
        inp_path = Path(td) / "network.inp"
        inp_path.write_text(inp_text)

        d = epanet(str(inp_path))
        try:
            # One-shot steady-state solve
            d.solveCompleteHydraulics()

            node_ids = d.getNodeNameID()
            link_ids = d.getLinkNameID()
            # Try the correctly-spelled method first; fall back to the
            # historical typo that still exists in some epyt releases.
            try:
                head_all = d.getNodeHydraulicHead()
            except AttributeError:
                head_all = d.getNodeHydaulicHead()
            pressure_all = d.getNodePressure()
            flows = d.getLinkFlows()
            velocities = d.getLinkVelocity()
        finally:
            d.unload()

    j_idx = node_ids.index("J")
    result = {
        "node_ids": list(node_ids),
        "link_ids": list(link_ids),
        "head_J_m": float(head_all[j_idx]),
        "pressure_J_m_head": float(pressure_all[j_idx]),
        "flows_Lps": [float(q) for q in flows],
        "velocities_m_s": [float(v) for v in velocities],
    }
    return result


def run_our_solver() -> dict:
    wp = water_properties(WATER_T_C)
    pipes = [
        {
            "P_pa": t["P_pa_abs"],
            "z_surface_m": t["z_surface_m"],
            "length_m": p["length_m"],
            "diameter_m": p["diameter_m"],
            "roughness_m": p["roughness_mm"] * 1e-3,
            "sum_K": p["sum_K_no_exit"],
        }
        for t, p in zip(TANKS, PIPES)
    ]
    fluid = {
        "density_kg_m3": wp["density_kg_m3"],
        "viscosity_pa_s": wp["viscosity_pa_s"],
        "z_J_m": Z_J,
    }
    return solve_three_reservoir_network(pipes, fluid)


def main():
    rho = water_properties(WATER_T_C)["density_kg_m3"]
    inp_text = build_inp()
    print("=== EPANET input file ===")
    print(inp_text)
    print("\n=== Running EPANET 2.2 ===")
    epa = run_epanet(inp_text)
    print(f"Nodes:        {epa['node_ids']}")
    print(f"Head at J:    {epa['head_J_m']:.4f} m (gauge)")
    print(f"Pressure at J:{epa['pressure_J_m_head']:.4f} m of water (gauge)")
    print(f"Flows (Lps):  {dict(zip(epa['link_ids'], epa['flows_Lps']))}")
    print(f"Velocities:   {dict(zip(epa['link_ids'], epa['velocities_m_s']))}")

    P_J_gauge_pa = rho * G * epa["pressure_J_m_head"]
    P_J_abs_kpa_epanet = (P_J_gauge_pa + P_ATM_PA) / 1000.0
    print(f"\nP_J absolute (EPANET):  {P_J_abs_kpa_epanet:.3f} kPa")

    print("\n=== Running our Python solver (same inputs, no exit K) ===")
    ours = run_our_solver()
    if "error" in ours:
        print(f"Solver error: {ours['error']}")
        return
    print(f"P_J absolute (ours):    {ours['junction_pressure_kpa']:.3f} kPa")
    for link_id, q_eps, our_pipe in zip(epa["link_ids"], epa["flows_Lps"], ours["pipes"]):
        print(f"  {link_id}: EPANET Q = {q_eps:+.4f} L/s   our Q = {our_pipe['flow_L_s']:+.4f} L/s   "
              f"v_us = {our_pipe['velocity_m_s']:+.3f} m/s  Re_us = {our_pipe['reynolds']:.0f}")

    delta_pct = (ours["junction_pressure_kpa"] - P_J_abs_kpa_epanet) / P_J_abs_kpa_epanet * 100
    print(f"\n=== Agreement ===")
    print(f"Our P_J vs EPANET P_J:  delta = {delta_pct:+.3f}%")
    print(f"Within 2% tolerance?    {'YES' if abs(delta_pct) < 2.0 else 'NO'}")


if __name__ == "__main__":
    main()
