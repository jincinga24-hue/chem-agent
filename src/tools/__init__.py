from .molecular import molecular_weight, molecular_properties, name_to_smiles
from .thermo import antoine_vapor_pressure, ideal_gas_volume
from .python_exec import python_exec
from .literature import arxiv_search

TOOL_FUNCTIONS = {
    "molecular_weight": molecular_weight,
    "molecular_properties": molecular_properties,
    "name_to_smiles": name_to_smiles,
    "antoine_vapor_pressure": antoine_vapor_pressure,
    "ideal_gas_volume": ideal_gas_volume,
    "python_exec": python_exec,
    "arxiv_search": arxiv_search,
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
]
