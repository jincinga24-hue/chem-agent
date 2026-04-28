from .molecular import molecular_weight, molecular_properties, name_to_smiles
from .thermo import antoine_vapor_pressure, ideal_gas_volume
from .python_exec import python_exec
from .literature import arxiv_search
from .fluids import (
    water_properties,
    pipe_roughness,
    standard_pipe_id,
    fitting_k,
    reynolds_number,
    friction_factor_colebrook,
    friction_factor_swamee_jain,
    solve_three_reservoir_network,
)
from .polymer import raft_kinetics, raft_target_dp
from .peptide import peptide_properties, helical_wheel_positions
from .knowledge import rag_search, rebuild_index

TOOL_FUNCTIONS = {
    "molecular_weight": molecular_weight,
    "molecular_properties": molecular_properties,
    "name_to_smiles": name_to_smiles,
    "antoine_vapor_pressure": antoine_vapor_pressure,
    "ideal_gas_volume": ideal_gas_volume,
    "python_exec": python_exec,
    "arxiv_search": arxiv_search,
    "water_properties": water_properties,
    "pipe_roughness": pipe_roughness,
    "standard_pipe_id": standard_pipe_id,
    "fitting_k": fitting_k,
    "reynolds_number": reynolds_number,
    "friction_factor_colebrook": friction_factor_colebrook,
    "friction_factor_swamee_jain": friction_factor_swamee_jain,
    "solve_three_reservoir_network": solve_three_reservoir_network,
    "raft_kinetics": raft_kinetics,
    "raft_target_dp": raft_target_dp,
    "peptide_properties": peptide_properties,
    "helical_wheel_positions": helical_wheel_positions,
    "rag_search": rag_search,
    "rebuild_index": rebuild_index,
}

TOOL_SCHEMAS = [
    {
        "name": "molecular_weight",
        "description": "Compute molecular weight (g/mol) of a molecule from its SMILES string. Use when a problem mentions a compound and needs its molar mass.",
        "input_schema": {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "SMILES string, e.g. 'CCO' for ethanol"},
            },
            "required": ["smiles"],
        },
    },
    {
        "name": "molecular_properties",
        "description": "Return molecular properties: MW, logP, H-bond donors/acceptors, rotatable bonds, TPSA. Use for compound characterization.",
        "input_schema": {
            "type": "object",
            "properties": {
                "smiles": {"type": "string"},
            },
            "required": ["smiles"],
        },
    },
    {
        "name": "name_to_smiles",
        "description": "Look up SMILES from a common chemical name. Supports a curated ChemE-relevant set (ethanol, water, benzene, methanol, aspirin, etc.). Returns error if unknown — fall back to asking the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "antoine_vapor_pressure",
        "description": "Compute vapor pressure (kPa) using Antoine equation: log10(P) = A - B/(C+T). Supports water, ethanol, methanol, benzene, toluene, acetone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "compound": {"type": "string", "description": "Compound name (lowercase)"},
                "temperature_c": {"type": "number", "description": "Temperature in Celsius"},
            },
            "required": ["compound", "temperature_c"],
        },
    },
    {
        "name": "ideal_gas_volume",
        "description": "Compute volume (L) of ideal gas: V = nRT/P. n in mol, T in K, P in kPa.",
        "input_schema": {
            "type": "object",
            "properties": {
                "moles": {"type": "number"},
                "temperature_k": {"type": "number"},
                "pressure_kpa": {"type": "number"},
            },
            "required": ["moles", "temperature_k", "pressure_kpa"],
        },
    },
    {
        "name": "python_exec",
        "description": "Execute Python code for arbitrary numerical calculations and optimization (reactor sizing, mass balance, distillation, parameter fitting). Has math, numpy (np), scipy, and statistics. Use scipy.optimize for fitting (least_squares, curve_fit, minimize), scipy.integrate, scipy.optimize.brentq / fsolve for root finding. MUST print() the final result. No file or network I/O.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code. Print final answer with print()."},
            },
            "required": ["code"],
        },
    },
    {
        "name": "arxiv_search",
        "description": "Search arxiv.org for scientific papers. Returns recent (sorted by date, newest first) papers matching the free-text query. Each paper has arxiv_id, title, authors, abstract summary, published date, category, and URL. Use when a problem asks for literature, recent research, or paper citations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text query, e.g. 'LLM agents for chemistry'"},
                "max_results": {"type": "integer", "description": "Number of results (1-20, default 5)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "water_properties",
        "description": "Density (kg/m^3) and dynamic viscosity (Pa·s) of liquid water at 1 atm for temperatures 0-100 C. Returns cited sources (Perry's / IAPWS). Use before any pipe-flow calculation that needs rho or mu.",
        "input_schema": {
            "type": "object",
            "properties": {
                "temperature_c": {"type": "number", "description": "Temperature in Celsius (0-100)"},
            },
            "required": ["temperature_c"],
        },
    },
    {
        "name": "pipe_roughness",
        "description": "Equivalent sand-grain roughness (mm) for a pipe material with a cited source (Moody 1944 / Crane TP-410 / Perry's / AS/NZS). Supported materials: drawn_tubing, commercial_steel, wrought_iron, galvanized_iron, cast_iron, concrete, riveted_steel, pvc, hdpe, copper, stainless_steel.",
        "input_schema": {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
            },
            "required": ["material"],
        },
    },
    {
        "name": "standard_pipe_id",
        "description": "Inside diameter for standard nominal pipe sizes with cited source. standard='steel_sch40' (ASME B36.10M-2018) or 'hdpe_pn16' (AS/NZS 4130:2018). nominal_size_mm is DN in mm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "standard": {"type": "string"},
                "nominal_size_mm": {"type": "number"},
            },
            "required": ["standard", "nominal_size_mm"],
        },
    },
    {
        "name": "fitting_k",
        "description": "Resistance coefficient K for pipe fittings (elbow_90_standard, elbow_45_standard, gate_valve_open, globe_valve_open, ball_valve_open, check_valve_swing, tee_through_run, tee_branch_flow, entrance_sharp, exit_to_tank). Source: Crane TP-410.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fitting": {"type": "string"},
            },
            "required": ["fitting"],
        },
    },
    {
        "name": "reynolds_number",
        "description": "Reynolds number Re = rho*v*D/mu with regime classification (laminar <2300, transitional, turbulent >=4000).",
        "input_schema": {
            "type": "object",
            "properties": {
                "density_kg_m3": {"type": "number"},
                "velocity_m_s": {"type": "number"},
                "diameter_m": {"type": "number"},
                "viscosity_pa_s": {"type": "number"},
            },
            "required": ["density_kg_m3", "velocity_m_s", "diameter_m", "viscosity_pa_s"],
        },
    },
    {
        "name": "friction_factor_colebrook",
        "description": "Darcy friction factor by iterative solution of the Colebrook-White equation. Use this for the best-accuracy friction factor in turbulent flow. For Re<2300 returns laminar 64/Re.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reynolds": {"type": "number"},
                "roughness_m": {"type": "number"},
                "diameter_m": {"type": "number"},
            },
            "required": ["reynolds", "roughness_m", "diameter_m"],
        },
    },
    {
        "name": "friction_factor_swamee_jain",
        "description": "Darcy friction factor by the explicit Swamee-Jain (1976) approximation. ~1% accurate vs Colebrook for 5e3<=Re<=1e8. Use for quick estimates or initial guesses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reynolds": {"type": "number"},
                "roughness_m": {"type": "number"},
                "diameter_m": {"type": "number"},
            },
            "required": ["reynolds", "roughness_m", "diameter_m"],
        },
    },
    {
        "name": "raft_kinetics",
        "description": "Predict RAFT polymerization kinetics: conversion x(t), number-average DP, Mn (g/mol), and dispersity Đ over time. Uses pseudo-steady-state radicals, 1st-order monomer consumption, and the Müller dispersity equation. Monomers: styrene, mma, ma, ba, acrylamide, vinyl_acetate. Initiators: aibn, bpo, v-65. CTAs: cdb, ddmat, cpadb, ctp. Concentrations in mol/L, T in Celsius, t in seconds. Use for any polymer synthesis problem with a RAFT agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "monomer": {"type": "string"},
                "initiator": {"type": "string"},
                "cta": {"type": "string", "description": "RAFT chain transfer agent"},
                "M0": {"type": "number", "description": "initial monomer conc, mol/L"},
                "I0": {"type": "number", "description": "initial initiator conc, mol/L"},
                "CTA0": {"type": "number", "description": "initial CTA conc, mol/L"},
                "T_C": {"type": "number", "description": "temperature in Celsius"},
                "t_final_s": {"type": "number", "description": "end time in seconds"},
                "n_points": {"type": "integer", "description": "samples in time series (default 50)"},
            },
            "required": ["monomer", "initiator", "cta", "M0", "I0", "CTA0", "T_C", "t_final_s"],
        },
    },
    {
        "name": "raft_target_dp",
        "description": "Inverse RAFT design: given a target degree of polymerization (DP) and monomer concentration, return the [CTA]_0 needed (assuming full conversion). Use when a problem asks 'how much CTA do I need to make a 100-mer of X'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "monomer": {"type": "string"},
                "cta": {"type": "string"},
                "M0": {"type": "number"},
                "target_DP": {"type": "number"},
            },
            "required": ["monomer", "cta", "M0", "target_DP"],
        },
    },
    {
        "name": "peptide_properties",
        "description": "Compute biophysical descriptors for a peptide sequence: MW, net charge at given pH (Henderson-Hasselbalch), mean Kyte-Doolittle hydrophobicity, hydrophobic moment μH for α-helix (δ=100°) and β-strand (δ=180°), Chou-Fasman helix propensity, and a heuristic AMP-likeness classification (Wimley-style: charge >=+3, μH >=0.4). Use for any antimicrobial peptide / SNAPP arm / helical peptide design problem. Input: standard 20 amino acids in single-letter code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sequence": {"type": "string", "description": "Single-letter amino acid sequence, e.g. 'KKLLKLLKLLKLL'"},
                "pH": {"type": "number", "description": "pH for charge calculation (default 7.4)"},
            },
            "required": ["sequence"],
        },
    },
    {
        "name": "helical_wheel_positions",
        "description": "Project peptide residues onto an α-helical wheel (100° per residue). Returns each residue's angular position and hydrophobicity. Use for visualizing/analyzing amphipathicity — hydrophobic residues cluster on one face of an amphipathic helix.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sequence": {"type": "string"},
            },
            "required": ["sequence"],
        },
    },
    {
        "name": "rag_search",
        "description": "Retrieval-augmented search over a corpus of chemistry/polymer chemistry text notes. Returns top-k passages with source citations and relevance scores. Use this BEFORE the python_exec or polymer/peptide tools when a problem mentions concepts you want grounded in the local corpus (e.g. 'what is the Mueller dispersity equation', 'design rule for AMP charge', 'CDB chain transfer constant'). The corpus currently covers: RAFT polymerization mechanism + kinetics, antimicrobial peptide design, SNAPPs, polymer dispersity. Lexical (BM25) match — phrase queries with the right keywords.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text query, e.g. 'RAFT chain transfer constant'"},
                "k": {"type": "integer", "description": "Number of passages to return (1-10, default 3)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "rebuild_index",
        "description": "Rebuild the RAG corpus index from disk. Use only if corpus files have been added or edited during the run. Returns chunk and term counts.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "solve_three_reservoir_network",
        "description": "Solve the 3-tank, 3-pipe junction problem. Each pipe dict needs: P_pa, z_surface_m (= z_tank + h_water), length_m, diameter_m, roughness_m, sum_K (sum of fitting resistance coefficients incl. entrance/exit). `fluid` dict needs density_kg_m3, viscosity_pa_s, z_J_m (junction elevation). Returns Q_i (m^3/s, sign = direction), Re, velocities, and junction pressure P_J.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pipes": {"type": "array"},
                "fluid": {"type": "object"},
            },
            "required": ["pipes", "fluid"],
        },
    },
]
